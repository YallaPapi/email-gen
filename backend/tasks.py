import os
import time
import pandas as pd
from celery import Celery
from openai import OpenAI
import re
from worker_models import WorkerModelAssigner

# Create Celery app
celery_app = Celery('tasks')
celery_app.config_from_object('celeryconfig')

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

model_assigner = WorkerModelAssigner()

def rate_limited_api_call():
    """Rate limiting between API calls"""
    time.sleep(0.2)

def clean_data(value):
    """Clean data values"""
    if pd.isna(value) or value == '' or str(value).lower() in ['nan', 'none', 'null']:
        return ''
    return str(value).strip()

def nuclear_clean_email(email_text):
    """NUCLEAR CLEANING - REMOVE EVERYTHING UNWANTED WITH REGEX"""
    import re
    
    # Step 1: Remove subject lines completely (any line starting with subject)
    email_text = re.sub(r'^Subject:.*?\n', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    email_text = re.sub(r'^subject:.*?\n', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Step 2: Split into lines and find greeting start
    lines = email_text.split('\n')
    start_index = 0
    
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean.startswith(('Hey ', 'Hi ', 'Hello ')):
            start_index = i
            break
    
    # Take only from greeting onwards
    lines = lines[start_index:]
    
    # Step 3: Remove signature patterns aggressively (including isolated words)
    signature_patterns = [
        r'^\s*Cheers!?\s*,?',
        r'^\s*Best!?\s*,?', 
        r'^\s*Thanks!?\s*,?',
        r'^\s*Regards?\s*,?',
        r'^\s*Sincerely\s*,?',
        r'^\s*\[Your Name\]\s*,?',
        r'^\s*\[.*\]\s*,?',
        r'^\s*Yours truly\s*,?',
        r'^\s*Warm regards\s*,?',
        r'^\s*Warm\s*$',  # Isolated "Warm" word
        r'^\s*Best\s*$',   # Isolated "Best" word  
        r'^\s*Cheers\s*$', # Isolated "Cheers" word
        r'^\s*Thanks\s*$'  # Isolated "Thanks" word
    ]
    
    # Filter out signature lines
    filtered_lines = []
    for line in lines:
        is_signature = False
        for pattern in signature_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                is_signature = True
                break
        if not is_signature:
            filtered_lines.append(line)
    
    # Step 4: Remove trailing empty lines and signature remnants (including isolated words)
    signature_words = ['cheers', 'best', 'thanks', 'regards', 'warm', 'sincerely']
    while (filtered_lines and 
           (not filtered_lines[-1].strip() or 
            filtered_lines[-1].strip().lower() in signature_words)):
        filtered_lines.pop()
    
    # Step 5: Join and aggressive final cleanup
    result = '\n'.join(filtered_lines)
    
    # Nuclear regex cleanup - remove any remaining unwanted patterns (including isolated words)
    result = re.sub(r'Subject:.*?\n', '', result, flags=re.IGNORECASE)
    result = re.sub(r'Cheers!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Best!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Thanks!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Regards[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Warm[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)  # Remove isolated "Warm"
    result = re.sub(r'\[Your Name\][,\s]*', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'\[.*\][,\s]*', '', result, flags=re.MULTILINE | re.IGNORECASE)
    
    # Additional cleanup for isolated signature words at line endings
    result = re.sub(r'\n\s*Warm\s*$', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\n\s*Best\s*$', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\n\s*Cheers\s*$', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\n\s*Thanks\s*$', '', result, flags=re.IGNORECASE)
    
    # Clean up multiple newlines and trailing whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    result = result.strip()
    
    return result

def update_status(job_id, status, progress, total):
    """Update job status to file and Redis"""
    status_file = f"uploads/{job_id}_status.txt"
    with open(status_file, "w") as f:
        f.write(f"{status},{progress},{total}")
    
    # Also update Redis
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.set(f"progress_{job_id}", progress)
        r.set(f"total_{job_id}", total)
    except Exception as e:
        print(f"Redis update failed: {e}")

def generate_email_sequence_for_row_direct(row_data, row_index, job_id):
    """Generate complete email sequence with ORIGINAL working prompts + nuclear cleaning"""
    try:
        print(f"Processing row {row_index}")
        
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        company_name = cleaned_data.get('organization_name') or cleaned_data.get('company', 'your company')
        
        # Handle industry
        industry_raw = cleaned_data.get('industry', '')
        if pd.isna(industry_raw) or industry_raw == '' or str(industry_raw).lower() in ['nan', 'none', 'null']:
            industry = 'your industry'
        else:
            industry = str(industry_raw).strip()
        
        model = model_assigner.get_worker_model()
        
        # STEP 1: Generate initial email - ORIGINAL WORKING PROMPT
        user_prompt_initial = f"""
Write a natural, conversational cold email using this contact information:
---
{prospect_info}
---
Write like you're a real person reaching out - natural, authentic, non-promotional tone.
Key guidelines:
- Start casually: "Hey {first_name}", "Hi {first_name}", "{first_name}, hope you're well"
- Mention you work with AI automation in a casual way.
- Reference their specific situation when possible.
- Keep it conversational and authentic.  
- End with EXACTLY these words: "If you're open to a chat, let me know - if not, all good." Use this exact phrase, no variations. NO apologetic language.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""

        system_prompt_initial = """
You are an AI assistant writing a cold email. Write ONLY the email body text with NO subject line, NO signatures, NO names, NO formal closings.
Write a short, casual email FROM a person who works in "AI automation" TO the prospect.
Follow all formatting rules. Be confident and direct. End with "if not, all good" ONLY.
Avoid spam trigger words. Use natural, conversational language.
CRITICAL: Do not include "Subject:", "Best,", "Cheers,", "[Your Name]", or any signatures.
"""
        
        rate_limited_api_call()
        
        completion_initial = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_initial},
                {"role": "user", "content": user_prompt_initial}
            ],
            temperature=0.8,
            max_tokens=200,
        )
        initial_email = completion_initial.choices[0].message.content.strip()
        initial_email = nuclear_clean_email(initial_email)
        
        # STEP 2: Generate follow-up 1 - ORIGINAL WORKING PROMPT  
        user_prompt_followup1 = f"""
You are an expert AI business consultant. Based on the following company data, identify the most pressing business challenge a company in the {industry} sector like {company_name} would face. Then, propose a specific, high-value AI solution (from our services: AI Chatbots, Automated Lead Gen, Database Reactivation) that directly solves that challenge. Frame it as a unique, tangible benefit. Do not be generic.

Company: {company_name}
Industry: {industry}
Contact: {first_name}

Write a follow-up email that shows you understand their industry challenges and offer a specific AI solution that would genuinely help their business.

Start with: "Hey {first_name}, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help."

End with: "Happy to hop on a call if this sounds useful - if not, all good!"

60-80 words. NO signatures. NO subject lines. NO names like "Best" or "Sincerely". ONLY the email body text.
"""
        
        system_prompt_followup1 = """
You are an AI automation expert. Write ONLY the email body text with no subject line, no signatures, no names, no formal closings.
Intelligently analyze the prospect's industry and recommend specific AI services.
Think like a business consultant. Be specific and industry-relevant, not generic.
Show you understand their industry. Be conversational and authentic.
CRITICAL: Do not include subject lines, signatures, "Best," "Sincerely," or any names.
"""
        
        rate_limited_api_call()
        
        completion_followup1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_followup1},
                {"role": "user", "content": user_prompt_followup1}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        followup_1_email = completion_followup1.choices[0].message.content.strip()
        followup_1_email = nuclear_clean_email(followup_1_email)
        
        # STEP 3: Generate follow-up 2 - ORIGINAL WORKING PROMPT
        user_prompt_followup2 = f"""
Write a final follow-up email to {first_name} at {company_name}.

Start with: "{first_name}, one more try?"

Say you'll assume they're not interested if you don't hear back and will leave them alone. Add some humor like "you probably deserve a break from the grind."

End with a short playful P.S.

50-70 words. NO signatures.
"""
        
        rate_limited_api_call()
        
        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are writing a final follow-up email. Follow the exact format provided. Add humor and personality. NO signatures."},
                {"role": "user", "content": user_prompt_followup2}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        followup_2_email = completion_followup2.choices[0].message.content.strip()
        followup_2_email = nuclear_clean_email(followup_2_email)
        
        return {
            "index": row_index,
            "row_data": row_data,
            "initial_email": initial_email,
            "followup_1": followup_1_email,
            "followup_2": followup_2_email,
            "status": "success",
            "model_used": model
        }
        
    except Exception as e:
        print(f"ERROR in row {row_index}: {str(e)}")
        return {
            "index": row_index,
            "row_data": row_data,
            "initial_email": f"ERROR: {str(e)[:200]}",
            "followup_1": "SKIPPED: Initial failed",
            "followup_2": "SKIPPED: Initial failed", 
            "status": "error",
            "model_used": "none"
        }

@celery_app.task(bind=True, max_retries=5, ignore_result=False)
def process_single_email(self, row_data, row_index, job_id):
    """Celery task version - uses same prompts as direct function for consistency"""
    try:
        print(f"🔥 CELERY TASK: Processing row {row_index} (Celery version)")
        
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        
        user_prompt = f"""
Write a natural, conversational cold email using this contact information:
---
{prospect_info}
---
Write like you're a real person reaching out - natural, authentic, non-promotional tone.
Key guidelines:
- Start casually: "Hey {first_name}", "Hi {first_name}", "{first_name}, hope you're well"
- Mention you work with AI automation in a casual way.
- Reference their specific situation when possible.
- Keep it conversational and authentic.
- End with EXACTLY these words: "If you're open to a chat, let me know - if not, all good." Use this exact phrase, no variations.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""
        
        system_prompt = """
You are writing a cold email. Write ONLY the email body text with NO subject line, NO signatures, NO names, NO formal closings.
Write FROM a person who works in "AI automation" TO that prospect.
Follow all formatting rules. Be confident and direct. Avoid spam trigger words.
CRITICAL: Do not include "Subject:", "Best,", "Cheers,", "[Your Name]", or any signatures.
MANDATORY: End with EXACTLY these words: "If you're open to a chat, let me know - if not, all good." No variations allowed.
"""
        
        rate_limited_api_call()
        model = model_assigner.get_worker_model()
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=200,
        )
        
        email_content = completion.choices[0].message.content.strip()
        email_content = nuclear_clean_email(email_content)
        
        return {
            "index": row_index,
            "row_data": row_data,
            "email": email_content,
            "status": "success",
            "model_used": model
        }
        
    except Exception as e:
        print(f"ERROR processing row {row_index}: {str(e)}")
        return {
            "index": row_index,
            "row_data": row_data,
            "email": f"ERROR: {str(e)[:200]}",
            "status": "error",
            "model_used": "none"
        }

def process_single_email_direct(row_data, row_index, job_id):
    """Direct function call version - no Celery decorators to avoid .get() deadlock"""
    try:
        print(f"⚡ DIRECT CALL: Processing row {row_index} (Direct version)")
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        
        user_prompt = f"""
Write a natural, conversational cold email using this contact information:
---
{prospect_info}
---
Write like you're a real person reaching out - natural, authentic, non-promotional tone.
Key guidelines:
- Start casually: "Hey {first_name}", "Hi {first_name}", "{first_name}, hope you're well"
- Mention you work with AI automation in a casual way.
- Reference their specific situation when possible.
- Keep it conversational and authentic.
- End with EXACTLY these words: "If you're open to a chat, let me know - if not, all good." Use this exact phrase, no variations.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""
        
        system_prompt = """
You are writing a cold email. Write ONLY the email body text with NO subject line, NO signatures, NO names, NO formal closings.
Write FROM a person who works in "AI automation" TO that prospect.
Follow all formatting rules. Be confident and direct. Avoid spam trigger words.
CRITICAL: Do not include "Subject:", "Best,", "Cheers,", "[Your Name]", or any signatures.
MANDATORY: End with EXACTLY these words: "If you're open to a chat, let me know - if not, all good." No variations allowed.
"""
        
        rate_limited_api_call()
        model = model_assigner.get_worker_model()
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=200,
        )
        
        email_text = completion.choices[0].message.content.strip()
        
        # Clean up any subject lines or signatures that might slip through
        email_text = nuclear_clean_email(email_text)
        
        return {
            "index": row_index,
            "row_data": row_data,
            "email": email_text,
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

@celery_app.task(bind=True, max_retries=3, ignore_result=False)
def process_spreadsheet_task(self, file_path, job_id, mode="single"):
    """Main task for processing spreadsheet"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        total_rows = len(df)
        update_status(job_id, "PROCESSING", 0, total_rows)
        
        results = []
        failed_count = 0
        
        for index, row in df.iterrows():
            try:
                row_data = row.to_dict()
                
                if mode == "sequence":
                    result = generate_email_sequence_for_row_direct(row_data, index, job_id)
                else:
                    result = process_single_email_direct(row_data, index, job_id)
                
                results.append(result)
                
                if result.get("status") == "error":
                    failed_count += 1
                
                update_status(job_id, "PROCESSING", index + 1, total_rows)
                
            except Exception as e:
                print(f"Error processing row {index}: {e}")
                failed_count += 1
                continue
        
        # Save results
        results_df = pd.DataFrame(results)
        output_path = f"uploads/result_{job_id}.xlsx"
        results_df.to_excel(output_path, index=False)
        
        final_status = "SUCCESS" if failed_count == 0 else f"PARTIAL_{failed_count}_ERRORS"
        update_status(job_id, final_status, total_rows, total_rows)
        
        return {"status": final_status, "output_file": output_path}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        raise e