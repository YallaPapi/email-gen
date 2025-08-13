import os
import time
import pandas as pd
from celery import Celery, chord
from openai import OpenAI
from dotenv import load_dotenv
import json
import threading
import redis
import random
import hashlib
from worker_models import WorkerModelAssigner

load_dotenv()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize worker model assigner
model_assigner = WorkerModelAssigner()

# Global rate limiter - 1 request per second
last_request_time = 0
request_lock = threading.Lock()

def rate_limited_api_call():
    """Ensure we don't exceed rate limits"""
    global last_request_time
    with request_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < 1.0:  # 1 request per second
            time.sleep(1.0 - time_since_last)
        last_request_time = time.time()

def update_status(job_id, status, progress, total):
    with open(f"uploads/{job_id}_status.txt", "w") as f:
        f.write(f"{status},{progress},{total}")

def generate_rewrite_instructions(seed_value):
    """Generate randomized rewrite instructions for variation"""
    random.seed(seed_value)
    
    instruction_type = random.randint(0, 3)
    
    if instruction_type == 0:
        # Slight variations on standard format
        return f"""Rewrite this email keeping the same professional structure but change:
- Opening: {random.choice([
    'Hi [name], I noticed [company]...',
    'Hey [name], saw that [company]...',
    '[Name], I see [company] is in...',
    'Hi [name], [company] being in [industry]...'
])}
- Introduce problems: {random.choice([
    'probably deals with...',
    'likely faces challenges like...',
    'might struggle with...',
    'probably encounters...'
])}
- List 3 AI solutions clearly as {random.choice(['bullets (•)', 'dashes (-)', 'numbers (1,2,3)'])}
- Closing: {random.choice([
    'Interested in learning more? Let\'s chat. If not, no worries!',
    'Want to explore how this could help? Quick call? If not, all good.',
    'Sound useful? Happy to discuss. Otherwise, no problem!',
    'Think this could help? Let me know. If not, totally fine!'
])}"""

    elif instruction_type == 1:
        # Slightly more direct version
        return f"""Rewrite more directly but keep professional:
- Opening: {random.choice([
    '[Name], quick question - [company] probably deals with...',
    'Hi [name], [company] in [industry] likely faces...',
    '[Name] - Know [company] struggles with...'
])}
- List the problems briefly, then say "We help with:"
- 3 AI solutions as {random.choice(['short bullets', 'quick points', 'brief list'])}:
  • Keep each solution under 10 words
  • Be specific to their industry
  • One must be lead gen or chatbots
- Closing: {random.choice([
    'Worth a quick chat? Let me know.',
    'Interested? Happy to show you how. If not, no worries.',
    'Make sense? Quick call this week?',
    'Sound helpful? Let\'s connect. Or not - your call.'
])}"""

    elif instruction_type == 2:
        # Helpful/consultative approach
        return f"""Rewrite with helpful tone but same structure:
- Opening: {random.choice([
    'Hi [name], I work with [industry] companies like [company]...',
    'Hey [name], helping [industry] businesses like [company]...',
    '[Name], I noticed [company] is in [industry]. We help similar companies...'
])}
- Mention problems: "Most face challenges with [list 2-3 problems]"
- Transition: {random.choice([
    'Our AI solutions help with:',
    'We address these with:',
    'Here\'s how AI can help:'
])}
- List 3 solutions as {random.choice(['bullets', 'dashes', 'numbers'])}
- Closing: {random.choice([
    'Happy to share how this works for others in [industry]. Interested?',
    'Can show you what we\'ve done for similar companies. Worth discussing?',
    'Would love to explore if this fits [company]. Quick chat?',
    'Let me know if you\'d like to learn more. No pressure!'
])}"""

    else:
        # Natural but professional
        return f"""Rewrite naturally but keep it professional:
- Opening: {random.choice([
    'Hi [name], saw [company] works in [industry]...',
    'Hey [name], I noticed [company] is a [industry] business...',
    '[Name], looking at [company], I imagine you deal with...'
])}
- Problems section: {random.choice([
    'I imagine you face [list problems]',
    'You probably deal with [list problems]',
    'Common challenges I see: [list problems]'
])}
- Solutions intro: {random.choice([
    'We\'ve built AI tools that help:',
    'Our AI solutions address these:',
    'Here\'s what we offer:'
])}
- List 3 solutions clearly
- Closing: {random.choice([
    'If this sounds useful, let\'s chat. If not, no worries at all!',
    'Interested? Love to show you. Not interested? Totally understand.',
    'Want to learn more? Happy to explain. Otherwise, all good!',
    'Think this could help [company]? Let me know either way.'
])}"""

@celery_app.task(bind=True, max_retries=5)
def process_single_email(self, row_data, row_index, job_id):
    """Two-step email generation for maximum variation"""
    try:
        # Extract key fields
        first_name = row_data.get('first_name') or row_data.get('name', 'there')
        company_name = row_data.get('organization_name', 'your company')
        industry = row_data.get('industry', 'your industry')
        org_description = row_data.get('organization_short_description', '')
        
        # Create unique seed for this email
        unique_string = f"{company_name}{first_name}{row_index}{job_id}"
        hash_seed = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
        
        # Get model assigned to this worker
        model = model_assigner.get_worker_model()
        
        # Log which worker and model we're using
        worker_info = f"Worker {os.getpid()}"
        if hasattr(self.request, 'hostname'):
            worker_info = self.request.hostname
        print(f"[{worker_info}] Using model: {model} for row {row_index}")
        
        # STEP 1: Generate base email with 3 AI solutions
        random.seed(hash_seed)
        base_system_prompt = f"""You are writing a cold email to someone in the {industry} industry.

Write a professional but friendly email that:
1. Opens with Hi [name] and mentions their company
2. States that companies in {industry} often deal with [2-3 specific problems]
3. Says "We help with:" and lists exactly 3 AI solutions:
   - ONE must be "AI lead generation" or "customer service chatbots"
   - The other 2 must be specific to {industry} problems
4. Ends with a soft CTA like "Interested? Let's chat. If not, no worries!"

Keep it 80-100 words. Be specific to {industry}, not generic."""

        base_user_prompt = f"""Write a cold email to:
Name: {first_name}
Company: {company_name}
Industry: {industry}
Description: {org_description if org_description else 'N/A'}

Include 3 specific AI solutions - one must be lead generation or chatbots, the other 2 specific to {industry}."""

        # First API call - generate base email
        rate_limited_api_call()
        
        try:
            completion1 = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": base_system_prompt},
                    {"role": "user", "content": base_user_prompt}
                ],
                temperature=0.8,
                max_tokens=120,  # Reduced from 150 to save costs
            )
            base_email = completion1.choices[0].message.content.strip()
        except Exception as api_error:
            if "429" in str(api_error) or "rate_limit" in str(api_error).lower():
                if "requests per day" in str(api_error) and self.request.retries >= 2:
                    email_text = f"DAILY_LIMIT_HIT: {str(api_error)}"
                    return {
                        "index": row_index,
                        "row_data": row_data,
                        "email": email_text,
                        "status": "daily_limit"
                    }
                else:
                    raise self.retry(exc=api_error, countdown=10 + (2 ** self.request.retries))
            else:
                raise
        
        # STEP 2: Rewrite for variation
        rewrite_instructions = generate_rewrite_instructions(hash_seed)
        
        rewrite_system_prompt = """You are rewriting an email to make it more varied and unique.
Follow the rewrite instructions EXACTLY.
Keep all 3 AI solutions but rephrase them.
Make it sound different from the original while keeping the same information."""

        rewrite_user_prompt = f"""Original email:
{base_email}

Rewrite instructions:
{rewrite_instructions}

Rewrite this email following these instructions exactly."""

        # Second API call - rewrite for variation
        rate_limited_api_call()
        
        try:
            completion2 = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": rewrite_system_prompt},
                    {"role": "user", "content": rewrite_user_prompt}
                ],
                temperature=0.9,  # Higher temperature for more variation
                max_tokens=120,  # Reduced from 150 to save costs
            )
            final_email = completion2.choices[0].message.content.strip()
        except Exception as api_error:
            # If second call fails, use base email
            final_email = base_email
        
        # Clean the email
        final_email = clean_email_text(final_email)
        
        return {
            "index": row_index,
            "row_data": row_data,
            "email": final_email,
            "status": "success",
            "model_used": model
        }
        
    except Exception as e:
        return {
            "index": row_index,
            "row_data": row_data,
            "email": f"ERROR: {str(e)}",
            "status": "error"
        }
    finally:
        # Update progress counter in Redis
        redis_key = f"progress_{job_id}"
        from celery import current_app
        current_app.backend.client.incr(redis_key)

def clean_email_text(email_text):
    """Clean email text - remove signatures, subject lines, etc."""
    if not email_text:
        return email_text
    
    # Remove subject lines
    lines = email_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip lines that look like signatures or metadata
        if line and not any(sig in line.lower() for sig in [
            'subject:', 'best regards', 'sincerely', '[your name]',
            'cheers', 'thanks', 'regards', 'best,', 'kind regards'
        ]):
            cleaned_lines.append(line)
    
    return '\n\n'.join(cleaned_lines)

@celery_app.task
def combine_results(results, job_id, total_rows):
    """Combine all results into final Excel file"""
    try:
        # Sort results by index to maintain original order
        sorted_results = sorted(results, key=lambda x: x['index'])
        
        # Build final dataframe
        final_data = []
        daily_limit_hit = False
        successful_emails = 0
        
        for result in sorted_results:
            row = result['row_data'].copy()
            
            # Clean email text to avoid Excel character issues
            email_text = result['email']
            if isinstance(email_text, str):
                # Remove problematic characters
                email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                # Remove control characters but keep newlines, tabs, carriage returns
                email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
            
            row['generated_email'] = email_text
            row['model_used'] = result.get('model_used', 'unknown')
            final_data.append(row)
            
            if "DAILY_LIMIT_HIT" in str(result['email']):
                daily_limit_hit = True
            elif result['status'] == 'success':
                successful_emails += 1
        
        # Save to Excel with CSV fallback
        df = pd.DataFrame(final_data)
        excel_file = f"uploads/result_{job_id}.xlsx"
        csv_file = f"uploads/result_{job_id}.csv"
        
        try:
            df.to_excel(excel_file, index=False)
            output_file = excel_file
        except Exception as excel_error:
            print(f"Excel save failed: {excel_error}, saving as CSV instead")
            df.to_csv(csv_file, index=False, encoding='utf-8')
            output_file = csv_file
        
        # Update final status
        if daily_limit_hit:
            update_status(job_id, f"PARTIAL_{successful_emails}_OF_{total_rows}", len(results), total_rows)
        else:
            update_status(job_id, "SUCCESS", total_rows, total_rows)
        
        # Clean up Redis progress counter
        from celery import current_app
        current_app.backend.client.delete(f"progress_{job_id}")
        
        return {"status": "SUCCESS", "file": output_file, "successful": successful_emails, "total": total_rows}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}

@celery_app.task
def process_spreadsheet_task(file_path: str, job_id: str):
    """Main task that creates subtasks for each row"""
    try:
        # Read the spreadsheet
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        total_rows = len(df)
        update_status(job_id, "PROCESSING", 0, total_rows)
        
        # Create a chord - parallel tasks with a callback
        from celery import chord
        
        # Create individual email tasks
        email_tasks = [
            process_single_email.s(row.to_dict(), index, job_id) 
            for index, row in df.iterrows()
        ]
        
        # Use chord to run all tasks and then combine results
        callback = combine_results.s(job_id, total_rows)
        chord(email_tasks)(callback)
        
        # Return immediately - the chord handles everything
        return {"status": "STARTED", "total_rows": total_rows}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}