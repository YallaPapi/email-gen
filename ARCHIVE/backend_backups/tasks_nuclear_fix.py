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

worker_last_times = {}
request_lock = threading.Lock()

def rate_limited_api_call():
    worker_id = os.getpid()
    
    with request_lock:
        if worker_id not in worker_last_times:
            worker_last_times[worker_id] = 0
        
        current_time = time.time()
        time_since_last = current_time - worker_last_times[worker_id]
        
        if time_since_last < 0.2:
            time.sleep(0.2 - time_since_last)
        
        worker_last_times[worker_id] = time.time()

def update_status(job_id, status, progress, total):
    with open(f"uploads/{job_id}_status.txt", "w") as f:
        f.write(f"{status},{progress},{total}")
    
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.set(f"progress_{job_id}", progress)
        r.set(f"total_{job_id}", total)
    except Exception as e:
        print(f"Redis update failed: {e}")

def clean_data(val):
    """Clean NaN/null values"""
    if pd.isna(val) or str(val).lower() in ['nan', 'none', 'null', '']:
        return ''
    return str(val).strip()

def nuclear_clean_email(email_text):
    """Nuclear cleaning - remove ALL unwanted formatting"""
    # Remove any line containing these patterns
    lines = email_text.split('\n')
    clean_lines = []
    
    skip_patterns = [
        'subject:', 'best,', 'cheers', 'regards', 'sincerely', 'thanks,',
        '[your name]', '[name]', '--', 'yours truly', 'warm regards'
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip lines with unwanted patterns
        if any(pattern in line.lower() for pattern in skip_patterns):
            continue
            
        # Skip lines that are just brackets
        if line.startswith('[') and line.endswith(']'):
            continue
            
        clean_lines.append(line)
    
    return '\n\n'.join(clean_lines)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, ignore_result=False)
def generate_email_sequence_for_row(self, row_data, row_index, job_id):
    try:
        print(f"Processing row {row_index}")
        
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        company_name = cleaned_data.get('organization_name') or cleaned_data.get('company', 'your company')
        
        industry = cleaned_data.get('industry', 'your industry')
        if not industry:
            industry = 'your industry'
        
        model = model_assigner.get_worker_model()
        
        # INITIAL EMAIL - NUCLEAR SIMPLE
        rate_limited_api_call()
        
        initial_prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}
Industry: {industry}

Write:
Hey {first_name},

[2-3 sentences about AI automation work and their company]

If you're open to a chat, let me know - if not, all good.

50-70 words total. Just the body text."""

        completion_initial = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": initial_prompt}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        initial_email = nuclear_clean_email(completion_initial.choices[0].message.content.strip())
        
        # FOLLOW-UP 1 - NUCLEAR SIMPLE
        rate_limited_api_call()
        
        followup1_prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}
Industry: {industry}

Write:
Hey {first_name}, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.

[1-2 sentences about specific AI solution for their industry]

Happy to hop on a call if this sounds useful - if not, all good!

60-80 words total. Just the body text."""

        completion_followup1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": followup1_prompt}
            ],
            temperature=0.7,
            max_tokens=150,
        )
        followup_1_email = nuclear_clean_email(completion_followup1.choices[0].message.content.strip())
        
        # FOLLOW-UP 2 - NUCLEAR SIMPLE
        rate_limited_api_call()
        
        followup2_prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}

Write:
{first_name}, one more try?

[1-2 sentences about assuming they're not interested, add some humor]

50-70 words total. Just the body text."""

        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": followup2_prompt}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        followup_2_email = nuclear_clean_email(completion_followup2.choices[0].message.content.strip())
        
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
    try:
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        company_name = cleaned_data.get('organization_name') or cleaned_data.get('company', 'your company')
        
        rate_limited_api_call()
        model = model_assigner.get_worker_model()
        
        prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}

Write:
Hey {first_name},

[2-3 sentences about AI automation work and their company]

If you're open to a chat, let me know - if not, all good.

50-70 words total. Just the body text."""

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        
        email_text = nuclear_clean_email(completion.choices[0].message.content.strip())
        
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
    # Same as above but direct function call
    try:
        print(f"DIRECT: Processing row {row_index}")
        
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        company_name = cleaned_data.get('organization_name') or cleaned_data.get('company', 'your company')
        
        industry = cleaned_data.get('industry', 'your industry')
        if not industry:
            industry = 'your industry'
        
        model = model_assigner.get_worker_model()
        
        # INITIAL EMAIL
        rate_limited_api_call()
        
        initial_prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}
Industry: {industry}

Write:
Hey {first_name},

[2-3 sentences about AI automation work and their company]

If you're open to a chat, let me know - if not, all good.

50-70 words total. Just the body text."""

        completion_initial = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": initial_prompt}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        initial_email = nuclear_clean_email(completion_initial.choices[0].message.content.strip())
        
        # FOLLOW-UP 1
        rate_limited_api_call()
        
        followup1_prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}
Industry: {industry}

Write:
Hey {first_name}, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.

[1-2 sentences about specific AI solution for their industry]

Happy to hop on a call if this sounds useful - if not, all good!

60-80 words total. Just the body text."""

        completion_followup1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": followup1_prompt}
            ],
            temperature=0.7,
            max_tokens=150,
        )
        followup_1_email = nuclear_clean_email(completion_followup1.choices[0].message.content.strip())
        
        # FOLLOW-UP 2
        rate_limited_api_call()
        
        followup2_prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}

Write:
{first_name}, one more try?

[1-2 sentences about assuming they're not interested, add some humor]

50-70 words total. Just the body text."""

        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": followup2_prompt}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        followup_2_email = nuclear_clean_email(completion_followup2.choices[0].message.content.strip())
        
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
            "model_used": "none",
            "error_type": type(e).__name__
        }

def process_single_email_direct(row_data, row_index, job_id):
    try:
        # Clean all data
        cleaned_data = {k: clean_data(v) for k, v in row_data.items()}
        
        prospect_info = '\n'.join([f"{k}: {v}" for k, v in cleaned_data.items() if v])
        first_name = cleaned_data.get('first_name') or cleaned_data.get('name', 'there')
        company_name = cleaned_data.get('organization_name') or cleaned_data.get('company', 'your company')
        
        rate_limited_api_call()
        model = model_assigner.get_worker_model()
        
        prompt = f"""Write ONLY the email body. No subject, no signature, no name.

Contact: {first_name}
Company: {company_name}

Write:
Hey {first_name},

[2-3 sentences about AI automation work and their company]

If you're open to a chat, let me know - if not, all good.

50-70 words total. Just the body text."""

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write only email body text. No subject lines, no signatures, no names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        
        email_text = nuclear_clean_email(completion.choices[0].message.content.strip())
        
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
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        total_rows = len(df)
        update_status(job_id, "PROCESSING", 0, total_rows)
        
        print(f"Processing {total_rows} rows in {mode} mode")
        
        all_results = []
        successful_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                row_data = row.to_dict()
                print(f"Processing row {index + 1}/{total_rows}")
                
                if mode == "sequence":
                    result = generate_email_sequence_for_row_direct(row_data, index, job_id)
                else:
                    result = process_single_email_direct(row_data, index, job_id)
                
                all_results.append(result)
                
                if result.get('status') == 'success':
                    successful_count += 1
                else:
                    error_count += 1
                    
                progress = index + 1
                update_status(job_id, "PROCESSING", progress, total_rows)
                print(f"Completed {progress}/{total_rows} - Success: {successful_count}, Errors: {error_count}")
                
            except Exception as row_error:
                print(f"Error processing row {index}: {row_error}")
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
        
        # Combine results
        print(f"Combining {len(all_results)} results")
        
        if mode == "sequence":
            combine_result = combine_sequence_results(all_results, job_id, total_rows)
        else:
            combine_result = combine_results(all_results, job_id, total_rows)
        
        print(f"Complete: {successful_count} successful, {error_count} errors")
        return {"status": "SUCCESS", "total_rows": total_rows, "successful": successful_count, "errors": error_count}
        
    except Exception as e:
        print(f"Failed: {str(e)}")
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}

def combine_sequence_results(results, job_id, total_rows):
    try:
        print(f"Combining {len(results)} sequence results")
        
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
            print(f"Saved sequence results to Excel: {excel_file}")
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
        
        print(f"Sequence processing complete: {successful_sequences}/{total_rows} successful sequences")
        
        return {"status": "SUCCESS", "file": output_file, "successful": successful_sequences, "total": total_rows}
        
    except Exception as e:
        print(f"Error combining sequence results: {str(e)}")
        update_status(job_id, "COMBINE_FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e), "error_type": type(e).__name__}

def combine_results(results, job_id, total_rows):
    try:
        print(f"Combining {len(results)} single email results")
        
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

@celery_app.task(ignore_result=False)
def process_spreadsheet_sequence_task(file_path: str, job_id: str):
    return process_spreadsheet_task(file_path, job_id, "sequence")