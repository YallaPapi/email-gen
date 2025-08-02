import os
import time
import pandas as pd
from celery import Celery, chord
from openai import OpenAI
from dotenv import load_dotenv
import json
import threading
import redis
from worker_models import WorkerModelAssigner

load_dotenv()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)

# Add robust Celery configuration for chord handling and production use
celery_app.conf.update(
    # Result backend configuration
    result_serializer='json',
    result_accept_content=['json'],
    result_expires=3600,  # 1 hour result expiration
    result_backend_always_retry=True,  # Retry on recoverable errors
    result_persistent=True,  # Ensure results persist across restarts
    
    # Task serialization and content
    accept_content=['json'],
    task_serializer='json',
    
    # Enable chord propagation and error handling
    task_track_started=True,
    task_always_eager=False,
    
    # Add chord-specific settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Improve error reporting
    task_send_sent_event=True,
    task_send_retry_event=True,
    
    # Chord backend settings for robust coordination
    result_chord_join_timeout=300,  # 5 minutes timeout for chord join
    
    # Redis-specific optimizations
    result_backend_transport_options={
        'result_chord_ordered': True,  # Maintain result order in groups
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {
            'TCP_KEEPINTVL': 1,
            'TCP_KEEPCNT': 3,
            'TCP_KEEPIDLE': 1,
        },
    },
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize worker model assigner
model_assigner = WorkerModelAssigner()

# Per-worker rate limiter - allows parallel processing
worker_last_times = {}
request_lock = threading.Lock()

def rate_limited_api_call():
    """Per-worker rate limiting instead of global serialization"""
    worker_id = os.getpid()  # Use process ID as unique identifier
    
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

@celery_app.task(bind=True, max_retries=5, ignore_result=False)
def process_single_email(self, row_data, row_index, job_id):
    """Process a single email - this can run in parallel"""
    try:
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in row_data.items()])
        
        # Get first_name for the prompt
        first_name = row_data.get('first_name') or row_data.get('name', 'there')
        
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
- End with "if you're open to a chat, let me know - if not, all good." NO apologetic language like "totally fine", "no pressure", "totally understand", etc.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""
        
        system_prompt = """
You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in "AI automation" TO that prospect.
It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company.
Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley.

CRITICAL: Avoid ALL spam trigger words including: free, guaranteed, act now, click here, limited time, urgent, instant, promise, risk-free, money back, get paid, earn money, cash, income, deal, promotion, sign up, call now, order now, exclusive, miracle, incredible, satisfaction guaranteed, once in lifetime, double your, 100% free, best price, lowest price, giveaway, prize, bonus, and 150+ other spam words. Use natural, conversational language instead.

TONE: Be confident and direct. End with "if not, all good" ONLY. Do NOT add any of these apologetic phrases: "totally fine", "no pressure", "no worries", "totally understand", "totally get it", "I understand", "completely understand", or any similar accommodating language. Be direct and confident.
"""
        
        # Rate limit API calls
        rate_limited_api_call()
        
        # Get model assigned to this worker
        model = model_assigner.get_worker_model()
        
        try:
            # Log which worker and model we're using
            worker_info = f"Worker {os.getpid()}"
            if hasattr(self.request, 'hostname'):
                worker_info = self.request.hostname
            print(f"[{worker_info}] Using model: {model} for row {row_index}")
            
            completion = client.chat.completions.create(
                model=model,  # Use worker-assigned model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=200,
            )
                
        except Exception as api_error:
            if "429" in str(api_error) or "rate_limit" in str(api_error).lower():
                # Check if it's daily limit (don't retry if daily limit hit)
                if "requests per day" in str(api_error) and self.request.retries >= 2:
                    # Daily limit hit - save what we have so far
                    email_text = f"DAILY_LIMIT_HIT: {str(api_error)}"
                else:
                    # Regular rate limit - retry with exponential backoff
                    raise self.retry(exc=api_error, countdown=10 + (2 ** self.request.retries))
            else:
                raise
        
        if 'completion' in locals():
            email_text = completion.choices[0].message.content.strip()
        # email_text already set if daily limit hit
        
        # Return the result with row index for ordering
        return {
            "index": row_index,
            "row_data": row_data,
            "email": email_text,
            "status": "success",
            "model_used": model if 'model' in locals() else "none"
        }
        
    except Exception as e:
        return {
            "index": row_index,
            "row_data": row_data,
            "email": f"ERROR: {str(e)}",
            "status": "error"
        }
    finally:
        # Update progress counter in Redis (thread-safe)
        redis_key = f"progress_{job_id}"
        from celery import current_app
        current_app.backend.client.incr(redis_key)



@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, ignore_result=False)
def process_email_sequence(self, row_data, row_index, job_id):
    """Generate complete email sequence: initial + 2 follow-ups"""
    # Ensure we always return a valid dictionary structure
    default_result = {
        "index": row_index,
        "row_data": row_data,
        "initial_email": "ERROR: Task failed to execute",
        "followup_1": "SKIPPED: Initial failed",
        "followup_2": "SKIPPED: Initial failed", 
        "status": "error",
        "model_used": "none"
    }
    
    try:
        print(f"🚀 PROCESS_EMAIL_SEQUENCE CALLED for row {row_index}")
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in row_data.items()])
        first_name = row_data.get('first_name') or row_data.get('name', 'there')
        company_name = row_data.get('organization_name') or row_data.get('company', 'your company')
        industry = row_data.get('industry', 'your industry')
        
        # Get model assigned to this worker
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
- End with "if you're open to a chat, let me know - if not, all good." NO apologetic language like "totally fine", "no pressure", "totally understand", etc.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""
        
        system_prompt_initial = """
You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in "AI automation" TO that prospect.
It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company.
Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley.

CRITICAL: Avoid ALL spam trigger words including: free, guaranteed, act now, click here, limited time, urgent, instant, promise, risk-free, money back, get paid, earn money, cash, income, deal, promotion, sign up, call now, order now, exclusive, miracle, incredible, satisfaction guaranteed, once in lifetime, double your, 100% free, best price, lowest price, giveaway, prize, bonus, and 150+ other spam words. Use natural, conversational language instead.

TONE: Be confident and direct. End with "if not, all good" ONLY. Do NOT add any of these apologetic phrases: "totally fine", "no pressure", "no worries", "totally understand", "totally get it", "I understand", "completely understand", or any similar accommodating language. Be direct and confident.
"""
        
        # Rate limit API calls
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
        
        # STEP 2: Generate first follow-up with intelligent AI service recommendations
        user_prompt_followup1 = f"""
Write a follow-up email to {first_name} at {company_name}.

Start with: "Hey {first_name}, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help."

Based on {company_name} being in {industry}, intelligently mention 2-3 of our AI services that would specifically benefit their type of business:

1. AI chatbots - Think about what this industry needs: customer support automation, lead qualification, technical assistance, appointment booking, etc. Mention the specific use case that makes sense for {industry} businesses.

2. Automated lead generation - Consider what type of leads this industry needs and how AI could identify and qualify prospects specifically for {industry} companies.

3. Database reactivation campaigns - AI systems that re-engage dormant customers with personalized outreach relevant to {industry} businesses.

Present these services as solutions that directly address what {industry} companies like {company_name} typically need, not generic AI mentions. Be specific about the value for their industry.

End with: "Happy to hop on a call if this sounds useful - if not, all good!"

60-80 words. NO signatures.
"""
        
        rate_limited_api_call()
        
        system_prompt_followup1 = """
You are an AI automation expert writing a follow-up email. Your job is to intelligently analyze the prospect's industry and recommend specific AI services that would genuinely benefit their type of business.

Think like a business consultant: What challenges does this industry typically face? What processes could be automated? What kind of customer interactions do they have? What types of leads do they need?

Be specific and industry-relevant, not generic. Don't just say "AI chatbots" - explain how chatbots would specifically help THEIR type of business. Show you understand their industry.

Follow the exact format and length requirements. Be conversational and authentic.
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
        
        # Return complete sequence
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
        # Log the full error for debugging
        print(f"ERROR in process_email_sequence row {row_index}: {str(e)}")
        
        # Check if this is a retryable error
        if ("429" in str(e) or "rate_limit" in str(e).lower() or 
            "timeout" in str(e).lower() or "connection" in str(e).lower()) and self.request.retries < 3:
            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        # Return detailed error information
        error_result = default_result.copy()
        error_result.update({
            "initial_email": f"ERROR: {str(e)[:200]}...",  # Truncate long errors
            "error_type": type(e).__name__,
            "retry_count": self.request.retries
        })
        return error_result
    finally:
        # Update progress counter in Redis (count as 1 sequence processed)
        redis_key = f"progress_{job_id}"
        from celery import current_app
        current_app.backend.client.incr(redis_key)

@celery_app.task(ignore_result=False)
def combine_sequence_results(results, job_id, total_rows):
    """Combine sequence results (initial + 2 follow-ups) into final Excel file"""
    try:
        # Handle case where results is None or empty
        if results is None:
            results = []
            print("🔥 COMBINE_SEQUENCE_RESULTS WARNING: results is None, using empty list")
        elif not isinstance(results, list):
            print(f"🔥 COMBINE_SEQUENCE_RESULTS WARNING: results is not a list: {type(results)}")
            results = [results] if results else []
        
        print(f"🔥 COMBINE_SEQUENCE_RESULTS CALLED: Combining sequence results from {len(results)} tasks")
        
        # Robust result filtering and validation
        valid_results = []
        invalid_results = []
        
        for i, result in enumerate(results):
            # Handle None or empty results
            if result is None:
                print(f"WARNING: Task {i} returned None")
                invalid_results.append({"index": i, "error": "Task returned None"})
                continue
            
            # Handle non-dict results
            if not isinstance(result, dict):
                print(f"WARNING: Task {i} returned non-dict: {type(result)} - {result}")
                invalid_results.append({"index": i, "error": f"Non-dict result: {type(result)}"})
                continue
            
            # Validate required fields
            required_fields = ['index', 'row_data', 'initial_email', 'followup_1', 'followup_2', 'status']
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                print(f"WARNING: Task {i} missing fields: {missing_fields}")
                # Create a default result for missing fields
                fixed_result = {
                    "index": result.get('index', i),
                    "row_data": result.get('row_data', {}),
                    "initial_email": result.get('initial_email', f"ERROR: Missing fields {missing_fields}"),
                    "followup_1": result.get('followup_1', "SKIPPED: Task incomplete"),
                    "followup_2": result.get('followup_2', "SKIPPED: Task incomplete"),
                    "status": "error",
                    "model_used": result.get('model_used', 'unknown')
                }
                valid_results.append(fixed_result)
            else:
                valid_results.append(result)
        
        # Log recovery stats
        print(f"Result validation: {len(valid_results)} valid, {len(invalid_results)} invalid")
        
        # For completely invalid results, create placeholder entries
        for invalid in invalid_results:
            placeholder = {
                "index": invalid['index'],
                "row_data": {"error": "Task failed completely"},
                "initial_email": f"ERROR: {invalid['error']}",
                "followup_1": "SKIPPED: Task failed",
                "followup_2": "SKIPPED: Task failed",
                "status": "error",
                "model_used": "none"
            }
            valid_results.append(placeholder)
        
        # Sort results by index to maintain original order
        sorted_results = sorted(valid_results, key=lambda x: x.get('index', 0))
        
        # Build final dataframe with enhanced error handling
        final_data = []
        successful_sequences = 0
        error_sequences = 0
        
        for result in sorted_results:
            try:
                # Safely copy row data
                row_data = result.get('row_data', {})
                if isinstance(row_data, dict):
                    row = row_data.copy()
                else:
                    row = {"original_data": str(row_data)}
                
                # Debug: print what keys are in the result
                print(f"Sequence result keys: {list(result.keys())}")
                
                # Clean email text to avoid Excel character issues
                def clean_email_text(email_text):
                    if isinstance(email_text, str):
                        email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                        email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
                    return email_text
            
                # Add the 3 emails as separate columns with robust error handling
                row['initial_email'] = clean_email_text(result.get('initial_email', 'ERROR: Not generated'))
                row['followup_1'] = clean_email_text(result.get('followup_1', 'ERROR: Not generated'))
                row['followup_2'] = clean_email_text(result.get('followup_2', 'ERROR: Not generated'))
                row['sequence_status'] = result.get('status', 'unknown')
                row['model_used'] = result.get('model_used', 'unknown')
                row['row_index'] = result.get('index', len(final_data))  # Add for debugging
                
                # Add error details if available
                if 'error_type' in result:
                    row['error_type'] = result['error_type']
                if 'retry_count' in result:
                    row['retry_count'] = result['retry_count']
                
                final_data.append(row)
                
                # Count success/error rates
                if result.get('status') == 'success':
                    successful_sequences += 1
                else:
                    error_sequences += 1
                    
            except Exception as row_error:
                print(f"Error processing result row: {row_error}")
                # Create emergency fallback row
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
        
        # Save to Excel with CSV fallback
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
        
        # Update final status with detailed reporting
        print(f"Final stats: {successful_sequences} successful, {error_sequences} errors, {len(final_data)} total rows")
        
        if successful_sequences == total_rows:
            update_status(job_id, "SUCCESS", total_rows, total_rows)
        elif successful_sequences > 0:
            update_status(job_id, f"PARTIAL_{successful_sequences}_OF_{total_rows}", len(final_data), total_rows)
        else:
            update_status(job_id, f"FAILED_ALL_{error_sequences}_ERRORS", len(final_data), total_rows)
        
        # Clean up Redis progress counter
        from celery import current_app
        current_app.backend.client.delete(f"progress_{job_id}")
        
        print(f"Sequence processing complete: {successful_sequences}/{total_rows} successful sequences")
        
        return {"status": "SUCCESS", "file": output_file, "successful": successful_sequences, "total": total_rows}
        
    except Exception as e:
        print(f"Error combining sequence results: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Results received: {len(results) if results else 0}")
        
        # Attempt to save partial results if any exist
        try:
            if results and len(results) > 0:
                print("Attempting to save partial results...")
                
                # Filter out completely invalid results
                salvageable_results = []
                for i, result in enumerate(results):
                    if result is not None and isinstance(result, dict):
                        # Ensure minimum required fields
                        if 'row_data' not in result:
                            result['row_data'] = {f"error_row_{i}": "Missing row data"}
                        if 'index' not in result:
                            result['index'] = i
                        salvageable_results.append(result)
                
                if salvageable_results:
                    # Recursive call with cleaned data
                    print(f"Attempting recovery with {len(salvageable_results)} salvageable results")
                    return combine_sequence_results(salvageable_results, job_id, total_rows)
        
        except Exception as recovery_error:
            print(f"Recovery attempt also failed: {recovery_error}")
        
        update_status(job_id, "COMBINE_FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e), "error_type": type(e).__name__}

@celery_app.task(ignore_result=False)
def combine_results(results, job_id, total_rows):
    """Combine all results into final Excel file"""
    try:
        print(f"⚠️ COMBINE_RESULTS CALLED (should not be called for sequence mode): {len(results)} tasks")
        # Sort results by index to maintain original order
        sorted_results = sorted(results, key=lambda x: x['index'])
        
        # Build final dataframe
        final_data = []
        daily_limit_hit = False
        successful_emails = 0
        
        for result in sorted_results:
            row = result['row_data'].copy()
            
            # Debug: print what keys are in the result
            print(f"Result keys: {list(result.keys())}")
            
            # Handle both old single email format and new sequence format
            if 'initial_email' in result:
                # New sequence format with 3 emails
                print("Using sequence format")
                def clean_email_text(email_text):
                    if isinstance(email_text, str):
                        email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                        email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
                    return email_text
                
                row['initial_email'] = clean_email_text(result.get('initial_email', ''))
                row['followup_1'] = clean_email_text(result.get('followup_1', ''))
                row['followup_2'] = clean_email_text(result.get('followup_2', ''))
                row['sequence_status'] = result.get('status', 'unknown')
            else:
                # Old single email format (for backward compatibility)
                email_text = result['email']
                if isinstance(email_text, str):
                    email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                    email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
                
                row['generated_email'] = email_text
            
            # Add model info for tracking
            row['model_used'] = result.get('model_used', 'unknown')
            final_data.append(row)
            
            # Check for daily limit hit in any email field
            result_text = str(result.get('email', '')) + str(result.get('initial_email', '')) + str(result.get('followup_1', '')) + str(result.get('followup_2', ''))
            if "DAILY_LIMIT_HIT" in result_text:
                daily_limit_hit = True
            elif result['status'] == 'success':
                successful_emails += 1
        
        # Save to Excel (even partial results), with CSV fallback
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

@celery_app.task(ignore_result=False)
def process_spreadsheet_task(file_path: str, job_id: str, mode: str = "single"):
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
        
        # Route based on mode parameter
        print(f"Received mode parameter: '{mode}'")
        if mode == "sequence":
            print(f"Processing in SEQUENCE mode - will generate 3 emails per row")
            # Create email sequence tasks (generates 3 emails per row)
            email_tasks = [
                process_email_sequence.s(row.to_dict(), index, job_id) 
                for index, row in df.iterrows()
            ]
            # Use sequence-specific combine function
            callback = combine_sequence_results.s(job_id, total_rows)
        else:
            print(f"Processing in SINGLE mode - will generate 1 email per row")
            # Create individual email tasks (generates 1 email per row)
            email_tasks = [
                process_single_email.s(row.to_dict(), index, job_id) 
                for index, row in df.iterrows()
            ]
            # Use regular combine function
            callback = combine_results.s(job_id, total_rows)
        
        # Simple, reliable chord creation
        try:
            print(f"Creating chord with {len(email_tasks)} tasks and callback")
            chord_result = chord(email_tasks)(callback)
            print(f"Chord created successfully with ID: {chord_result.id}")
            
        except Exception as chord_error:
            print(f"Chord creation failed: {chord_error}")
            update_status(job_id, "CHORD_CREATION_FAILED", 0, total_rows)
            return {"status": "FAILURE", "error": f"Chord creation failed: {str(chord_error)}"}
        
        # Return immediately - the chord handles everything
        return {"status": "STARTED", "total_rows": total_rows}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}

@celery_app.task(ignore_result=False)
def process_spreadsheet_sequence_task(file_path: str, job_id: str):
    """Main task that creates email sequence subtasks (initial + 2 follow-ups)"""
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
        
        # Create email sequence tasks (generates 3 emails per row)
        email_tasks = [
            process_email_sequence.s(row.to_dict(), index, job_id) 
            for index, row in df.iterrows()
        ]
        
        # Use chord to run all tasks and then combine sequence results
        callback = combine_sequence_results.s(job_id, total_rows)
        chord(email_tasks)(callback)
        
        # Return immediately - the chord handles everything
        return {"status": "STARTED", "total_rows": total_rows, "mode": "sequence"}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}