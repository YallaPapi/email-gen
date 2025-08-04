import os
import time
import pandas as pd
from celery import Celery
from openai import OpenAI
from dotenv import load_dotenv
import threading
import redis
from worker_models import WorkerModelAssigner

load_dotenv()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)

# Simplified Celery configuration - NO CHORD SUPPORT NEEDED
celery_app.conf.update(
    result_serializer='json',
    accept_content=['json'],
    task_serializer='json',
    result_expires=3600,
    task_track_started=True,
    task_always_eager=False,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model_assigner = WorkerModelAssigner()

# Rate limiter
worker_last_times = {}
request_lock = threading.Lock()

def clean_email_output(email_text):
    """Aggressively remove subject lines, signatures, and other unwanted formatting"""
    lines = email_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip subject lines
        if 'subject:' in line.lower():
            continue
        # Skip ALL signatures and closings
        if any(sig in line.lower() for sig in ['best,', 'best regards', 'sincerely', 'thanks,', 'cheers', 'regards']):
            continue
        # Skip lines with brackets (names/placeholders)
        if '[' in line and ']' in line:
            continue
        # Skip signature dashes and empty lines
        if line.startswith('--') or line == '':
            continue
        cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines).strip()
    
    # Additional cleaning - remove any remaining signature patterns
    result = result.replace('Subject: AI Automation for', '').replace('Subject:', '')
    result = result.replace('[Your Name]', '').replace('Cheers,', '').replace('Best,', '')
    
    return result.strip()

def rate_limited_api_call():
    """Per-worker rate limiting"""
    worker_id = os.getpid()
    
    with request_lock:
        if worker_id not in worker_last_times:
            worker_last_times[worker_id] = 0
        
        current_time = time.time()
        time_since_last = current_time - worker_last_times[worker_id]
        
        if time_since_last < 0.2:  # 5 requests per second per worker
            time.sleep(0.2 - time_since_last)
        
        worker_last_times[worker_id] = time.time()

def update_status(job_id, status, progress, total):
    with open(f"uploads/{job_id}_status.txt", "w") as f:
        f.write(f"{status},{progress},{total}")
    
    # Also update Redis for real-time progress tracking
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.set(f"progress_{job_id}", progress)
        r.set(f"total_{job_id}", total)
    except Exception as e:
        print(f"Redis update failed: {e}")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, ignore_result=False)
def generate_email_sequence_for_row(self, row_data, row_index, job_id):
    """OPERATION PHOENIX: Generate complete email sequence for a single row (SEQUENTIAL)"""
    try:
        print(f"🔥 PHOENIX: Processing row {row_index}")
        
        # Fix the 'nan sector' issue - clean up row_data first
        cleaned_row_data = {}
        for col, val in row_data.items():
            if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'none', 'null']:
                cleaned_row_data[col] = ''
            else:
                cleaned_row_data[col] = str(val).strip()
        
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in cleaned_row_data.items() if val])
        first_name = cleaned_row_data.get('first_name') or cleaned_row_data.get('name', 'there')
        company_name = cleaned_row_data.get('organization_name') or cleaned_row_data.get('company', 'your company')
        
        # Fix the 'nan sector' issue - handle NaN/None/empty industry values
        industry_raw = cleaned_row_data.get('industry', '')
        if pd.isna(industry_raw) or industry_raw == '' or str(industry_raw).lower() in ['nan', 'none', 'null']:
            industry = 'your industry'
        else:
            industry = str(industry_raw).strip()
        
        model = model_assigner.get_worker_model()
        
        # STEP 1: Generate initial email
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
- End with "if you're open to a chat, let me know - if not, all good." NO apologetic language.
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
        
        # Clean up any subject lines or signatures that might slip through
        initial_email = clean_email_output(initial_email)
        
        # STEP 2: INTELLIGENT FOLLOW-UP (Per mandate: Remove hardcoded industry examples)
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
        
        rate_limited_api_call()
        
        system_prompt_followup1 = """
You are an AI automation expert. Write ONLY the email body text with no subject line, no signatures, no names, no formal closings.
Intelligently analyze the prospect's industry and recommend specific AI services.
Think like a business consultant. Be specific and industry-relevant, not generic.
Show you understand their industry. Be conversational and authentic.
CRITICAL: Do not include subject lines, signatures, "Best," "Sincerely," or any names.
"""
        
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
        
        # Clean up any subject lines or signatures that might slip through
        followup_1_email = clean_email_output(followup_1_email)
        
        # STEP 3: Generate second follow-up
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
        
        # Clean up any subject lines or signatures that might slip through
        followup_2_email = clean_email_output(followup_2_email)
        
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
        print(f"ERROR in generate_email_sequence_for_row row {row_index}: {str(e)}")
        
        if (("429" in str(e) or "rate_limit" in str(e).lower()) and self.request.retries < 3):
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            "index": row_index,
            "row_data": row_data,
            "initial_email": f"ERROR: {str(e)[:200]}",
            "followup_1": "SKIPPED: Initial failed",
            "followup_2": "SKIPPED: Initial failed", 
            "status": "error",
            "model_used": "none",
            "error_type": type(e).__name__,
            "retry_count": self.request.retries
        }

@celery_app.task(bind=True, max_retries=5, ignore_result=False)
def process_single_email(self, row_data, row_index, job_id):
    """Process a single email for backward compatibility"""
    try:
        # Fix the 'nan sector' issue - clean up row_data first
        cleaned_row_data = {}
        for col, val in row_data.items():
            if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'none', 'null']:
                cleaned_row_data[col] = ''
            else:
                cleaned_row_data[col] = str(val).strip()
        
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in cleaned_row_data.items() if val])
        first_name = cleaned_row_data.get('first_name') or cleaned_row_data.get('name', 'there')
        
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
- End with "if you're open to a chat, let me know - if not, all good."
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
        email_text = clean_email_output(email_text)
        
        return {
            "index": row_index,
            "row_data": row_data,
            "email": email_text,
            "status": "success",
            "model_used": model
        }
        
    except Exception as e:
        if "429" in str(e) and self.request.retries < 3:
            raise self.retry(exc=e, countdown=10 + (2 ** self.request.retries))
        
        return {
            "index": row_index,
            "row_data": row_data,
            "email": f"ERROR: {str(e)}",
            "status": "error"
        }

def generate_email_sequence_for_row_direct(row_data, row_index, job_id):
    """Direct function call version - no Celery decorators to avoid .get() deadlock"""
    try:
        print(f"🔥 PHOENIX DIRECT: Processing row {row_index}")
        
        # Fix the 'nan sector' issue - clean up row_data first
        cleaned_row_data = {}
        for col, val in row_data.items():
            if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'none', 'null']:
                cleaned_row_data[col] = ''
            else:
                cleaned_row_data[col] = str(val).strip()
        
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in cleaned_row_data.items() if val])
        first_name = cleaned_row_data.get('first_name') or cleaned_row_data.get('name', 'there')
        company_name = cleaned_row_data.get('organization_name') or cleaned_row_data.get('company', 'your company')
        
        # Fix the 'nan sector' issue - handle NaN/None/empty industry values
        industry_raw = cleaned_row_data.get('industry', '')
        if pd.isna(industry_raw) or industry_raw == '' or str(industry_raw).lower() in ['nan', 'none', 'null']:
            industry = 'your industry'
        else:
            industry = str(industry_raw).strip()
        
        model = model_assigner.get_worker_model()
        
        # STEP 1: Generate initial email
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
- End with "if you're open to a chat, let me know - if not, all good." NO apologetic language.
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
        
        # Clean up any subject lines or signatures that might slip through
        initial_email = clean_email_output(initial_email)
        
        # STEP 2: INTELLIGENT FOLLOW-UP (Per mandate: Remove hardcoded industry examples)
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
        
        rate_limited_api_call()
        
        system_prompt_followup1 = """
You are an AI automation expert. Write ONLY the email body text with no subject line, no signatures, no names, no formal closings.
Intelligently analyze the prospect's industry and recommend specific AI services.
Think like a business consultant. Be specific and industry-relevant, not generic.
Show you understand their industry. Be conversational and authentic.
CRITICAL: Do not include subject lines, signatures, "Best," "Sincerely," or any names.
"""
        
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
        
        # Clean up any subject lines or signatures that might slip through
        followup_1_email = clean_email_output(followup_1_email)
        
        # STEP 3: Generate second follow-up
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
        
        # Clean up any subject lines or signatures that might slip through
        followup_2_email = clean_email_output(followup_2_email)
        
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
        print(f"ERROR in generate_email_sequence_for_row_direct row {row_index}: {str(e)}")
        
        return {
            "index": row_index,
            "row_data": row_data,
            "initial_email": f"ERROR: {str(e)[:200]}",
            "followup_1": "SKIPPED: Initial failed",
            "followup_2": "SKIPPED: Initial failed", 
            "status": "error",
            "model_used": "none",
            "error_type": type(e).__name__
        }

def process_single_email_direct(row_data, row_index, job_id):
    """Direct function call version - no Celery decorators to avoid .get() deadlock"""
    try:
        # Fix the 'nan sector' issue - clean up row_data first
        cleaned_row_data = {}
        for col, val in row_data.items():
            if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'none', 'null']:
                cleaned_row_data[col] = ''
            else:
                cleaned_row_data[col] = str(val).strip()
        
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in cleaned_row_data.items() if val])
        first_name = cleaned_row_data.get('first_name') or cleaned_row_data.get('name', 'there')
        
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
- End with "if you're open to a chat, let me know - if not, all good."
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
        email_text = clean_email_output(email_text)
        
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

@celery_app.task(ignore_result=False)
def process_spreadsheet_task(file_path: str, job_id: str, mode: str = "single"):
    """OPERATION PHOENIX: Main task with sequential processing (NO CHORDS)"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        total_rows = len(df)
        update_status(job_id, "PROCESSING", 0, total_rows)
        
        print(f"🔥 OPERATION PHOENIX: Processing {total_rows} rows in {mode} mode - SEQUENTIAL")
        
        all_results = []
        successful_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                row_data = row.to_dict()
                print(f"🔥 Processing row {index + 1}/{total_rows}")
                
                if mode == "sequence":
                    # Call function directly to avoid Celery .get() deadlock
                    result = generate_email_sequence_for_row_direct(row_data, index, job_id)
                else:
                    # Call function directly to avoid Celery .get() deadlock  
                    result = process_single_email_direct(row_data, index, job_id)
                
                all_results.append(result)
                
                if result.get('status') == 'success':
                    successful_count += 1
                else:
                    error_count += 1
                    
                progress = index + 1
                update_status(job_id, "PROCESSING", progress, total_rows)
                print(f"🔥 Completed {progress}/{total_rows} - Success: {successful_count}, Errors: {error_count}")
                
            except Exception as row_error:
                print(f"🔥 Error processing row {index}: {row_error}")
                error_result = {
                    "index": index,
                    "row_data": row.to_dict(),
                    "status": "error",
                    "error": str(row_error)
                }
                
                if mode == "sequence":
                    error_result.update({
                        "initial_email": f"ERROR: {str(row_error)}",
                        "followup_1": "SKIPPED: Row failed",
                        "followup_2": "SKIPPED: Row failed"
                    })
                else:
                    error_result["email"] = f"ERROR: {str(row_error)}"
                    
                all_results.append(error_result)
                error_count += 1
        
        # Combine results (call synchronously - no chords)
        print(f"🔥 PHOENIX: Combining {len(all_results)} results")
        
        if mode == "sequence":
            combine_result = combine_sequence_results(all_results, job_id, total_rows)
        else:
            combine_result = combine_results(all_results, job_id, total_rows)
        
        print(f"🔥 OPERATION PHOENIX COMPLETE: {successful_count} successful, {error_count} errors")
        return {"status": "SUCCESS", "total_rows": total_rows, "successful": successful_count, "errors": error_count}
        
    except Exception as e:
        print(f"🔥 OPERATION PHOENIX FAILED: {str(e)}")
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}

def combine_sequence_results(results, job_id, total_rows):
    """Combine sequence results - DIRECT FUNCTION CALL (NO CHORD)"""
    try:
        print(f"🔥 COMBINE_SEQUENCE_RESULTS: Combining {len(results)} sequence results")
        
        final_data = []
        successful_sequences = 0
        error_sequences = 0
        
        for result in results:
            try:
                row_data = result.get('row_data', {})
                if isinstance(row_data, dict):
                    row = row_data.copy()
                else:
                    row = {"original_data": str(row_data)}
                
                def clean_email_text(email_text):
                    if isinstance(email_text, str):
                        email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                        email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
                    return email_text
            
                row['initial_email'] = clean_email_text(result.get('initial_email', 'ERROR: Not generated'))
                row['followup_1'] = clean_email_text(result.get('followup_1', 'ERROR: Not generated'))
                row['followup_2'] = clean_email_text(result.get('followup_2', 'ERROR: Not generated'))
                row['sequence_status'] = result.get('status', 'unknown')
                row['model_used'] = result.get('model_used', 'unknown')
                row['row_index'] = result.get('index', len(final_data))
                
                final_data.append(row)
                
                if result.get('status') == 'success':
                    successful_sequences += 1
                else:
                    error_sequences += 1
                    
            except Exception as row_error:
                print(f"Error processing result row: {row_error}")
                fallback_row = {
                    "initial_email": f"PROCESSING_ERROR: {str(row_error)}",
                    "followup_1": "SKIPPED: Row processing failed",
                    "followup_2": "SKIPPED: Row processing failed",
                    "sequence_status": "processing_error",
                    "model_used": "none",
                    "row_index": len(final_data)
                }
                final_data.append(fallback_row)
                error_sequences += 1
        
        # Save to Excel
        df = pd.DataFrame(final_data)
        excel_file = f"uploads/result_{job_id}.xlsx"
        csv_file = f"uploads/result_{job_id}.csv"
        
        try:
            df.to_excel(excel_file, index=False)
            output_file = excel_file
            print(f"🔥 Saved sequence results to Excel: {excel_file}")
        except Exception as excel_error:
            print(f"Excel save failed: {excel_error}, saving as CSV instead")
            df.to_csv(csv_file, index=False, encoding='utf-8')
            output_file = csv_file
        
        if successful_sequences == total_rows:
            update_status(job_id, "SUCCESS", total_rows, total_rows)
        elif successful_sequences > 0:
            update_status(job_id, f"PARTIAL_{successful_sequences}_OF_{total_rows}", len(final_data), total_rows)
        else:
            update_status(job_id, f"FAILED_ALL_{error_sequences}_ERRORS", len(final_data), total_rows)
        
        print(f"🔥 Sequence processing complete: {successful_sequences}/{total_rows} successful sequences")
        
        return {"status": "SUCCESS", "file": output_file, "successful": successful_sequences, "total": total_rows}
        
    except Exception as e:
        print(f"Error combining sequence results: {str(e)}")
        update_status(job_id, "COMBINE_FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e), "error_type": type(e).__name__}

def combine_results(results, job_id, total_rows):
    """Combine single email results - DIRECT FUNCTION CALL (NO CHORD)"""
    try:
        print(f"🔥 COMBINE_RESULTS: Combining {len(results)} single email results")
        
        sorted_results = sorted(results, key=lambda x: x['index'])
        final_data = []
        successful_emails = 0
        
        for result in sorted_results:
            row = result['row_data'].copy()
            
            email_text = result['email']
            if isinstance(email_text, str):
                email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
            
            row['generated_email'] = email_text
            row['model_used'] = result.get('model_used', 'unknown')
            final_data.append(row)
            
            if result['status'] == 'success':
                successful_emails += 1
        
        # Save to Excel
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
        
        update_status(job_id, "SUCCESS", total_rows, total_rows)
        
        return {"status": "SUCCESS", "file": output_file, "successful": successful_emails, "total": total_rows}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}

# Deprecated chord functions remain for API compatibility but are not used
@celery_app.task(ignore_result=False)
def process_spreadsheet_sequence_task(file_path: str, job_id: str):
    """DEPRECATED: Use process_spreadsheet_task with mode='sequence' instead"""
    return process_spreadsheet_task(file_path, job_id, "sequence")