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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize worker model assigner
model_assigner = WorkerModelAssigner()

# Configuration for large-scale processing
CHUNK_SIZE = 1000  # Process in chunks of 1000 emails
MAX_RETRIES = 3

def update_status(job_id, status, progress, total):
    with open(f"uploads/{job_id}_status.txt", "w") as f:
        f.write(f"{status},{progress},{total}")

@celery_app.task(bind=True, max_retries=3)
def process_email_chunk(self, chunk_data, chunk_index, job_id, total_chunks):
    """Process a chunk of emails in parallel"""
    try:
        print(f"Processing chunk {chunk_index + 1}/{total_chunks} with {len(chunk_data)} emails")
        
        chunk_results = []
        successful_emails = 0
        
        # Get model assigned to this worker
        model = model_assigner.get_worker_model()
        worker_info = self.request.hostname if hasattr(self.request, 'hostname') else f"Worker {os.getpid()}"
        
        system_prompt = """
You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in "AI automation" TO that prospect.
It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company.
Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley.
"""
        
        for row_index, row_data in chunk_data:
            try:
                prospect_info = '\n'.join([f"{col}: {val}" for col, val in row_data.items()])
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
- End with if-then call CTA + "if not, all good/no worries/totally fine" with a smiley.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""
                
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
                successful_emails += 1
                
                chunk_results.append({
                    "index": row_index,
                    "row_data": row_data,
                    "email": email_text,
                    "status": "success",
                    "model_used": model
                })
                
            except Exception as e:
                print(f"Error processing row {row_index}: {str(e)}")
                chunk_results.append({
                    "index": row_index,
                    "row_data": row_data,
                    "email": f"ERROR: {str(e)}",
                    "status": "error",
                    "model_used": model
                })
                
                # For rate limits, wait and retry once
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    if self.request.retries < MAX_RETRIES:
                        print(f"Rate limit hit, retrying chunk {chunk_index} in 30 seconds...")
                        raise self.retry(exc=e, countdown=30)
        
        # Update progress in Redis (batch update)
        redis_key = f"progress_{job_id}"
        from celery import current_app
        current_app.backend.client.incrby(redis_key, len(chunk_data))
        
        print(f"[{worker_info}] Completed chunk {chunk_index + 1}/{total_chunks}: {successful_emails}/{len(chunk_data)} successful")
        
        return {
            "chunk_index": chunk_index,
            "results": chunk_results,
            "successful": successful_emails,
            "total": len(chunk_data),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Chunk {chunk_index} failed completely: {str(e)}")
        return {
            "chunk_index": chunk_index,
            "results": [],
            "successful": 0,
            "total": len(chunk_data) if 'chunk_data' in locals() else 0,
            "status": "error",
            "error": str(e)
        }

@celery_app.task
def combine_chunk_results(chunk_results, job_id, total_rows):
    """Combine all chunk results into final Excel file"""
    try:
        print(f"Combining results from {len(chunk_results)} chunks")
        
        # Flatten all results from all chunks
        all_results = []
        total_successful = 0
        total_processed = 0
        
        for chunk_result in chunk_results:
            if chunk_result['status'] == 'success':
                all_results.extend(chunk_result['results'])
                total_successful += chunk_result['successful']
                total_processed += chunk_result['total']
            else:
                print(f"Chunk {chunk_result['chunk_index']} failed: {chunk_result.get('error', 'Unknown error')}")
        
        if not all_results:
            update_status(job_id, "FAILURE", 0, 0)
            return {"status": "FAILURE", "error": "No results from any chunks"}
        
        # Sort results by index to maintain original order
        sorted_results = sorted(all_results, key=lambda x: x['index'])
        
        # Build final dataframe
        final_data = []
        actual_successful = 0
        
        for result in sorted_results:
            row = result['row_data'].copy()
            
            # Clean email text to avoid Excel character issues
            email_text = result['email']
            if isinstance(email_text, str):
                # Remove problematic characters that Excel can't handle
                email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                # Remove other control characters but keep newlines, tabs, carriage returns
                email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
            
            row['generated_email'] = email_text
            row['model_used'] = result.get('model_used', 'unknown')
            final_data.append(row)
            
            if result['status'] == 'success' and not result['email'].startswith('ERROR'):
                actual_successful += 1
        
        # Save to both CSV and Excel
        df = pd.DataFrame(final_data)
        
        # Save CSV first (more reliable)
        csv_file = f"uploads/result_{job_id}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # Try to save Excel, fallback to CSV if it fails
        excel_file = f"uploads/result_{job_id}.xlsx"
        try:
            df.to_excel(excel_file, index=False)
            output_file = excel_file
        except Exception as excel_error:
            print(f"Excel save failed: {excel_error}, using CSV instead")
            output_file = csv_file
        
        # Update final status
        if actual_successful == total_rows:
            update_status(job_id, "SUCCESS", total_rows, total_rows)
        else:
            update_status(job_id, f"PARTIAL_{actual_successful}_OF_{total_rows}", len(final_data), total_rows)
        
        # Clean up Redis progress counter
        from celery import current_app
        current_app.backend.client.delete(f"progress_{job_id}")
        
        print(f"Final results: {actual_successful}/{total_rows} successful emails generated")
        
        return {
            "status": "SUCCESS" if actual_successful > 0 else "FAILURE",
            "file": output_file,
            "successful": actual_successful,
            "total": total_rows,
            "processed": len(final_data)
        }
        
    except Exception as e:
        print(f"Error combining results: {str(e)}")
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}

@celery_app.task
def process_spreadsheet_task(file_path: str, job_id: str):
    """Main task that processes spreadsheet in manageable chunks"""
    try:
        # Read the spreadsheet
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        total_rows = len(df)
        print(f"Starting processing of {total_rows} rows in chunks of {CHUNK_SIZE}")
        update_status(job_id, "PROCESSING", 0, total_rows)
        
        # Initialize progress counter in Redis
        from celery import current_app
        current_app.backend.client.set(f"progress_{job_id}", 0)
        
        # Split data into chunks
        chunks = []
        for i in range(0, total_rows, CHUNK_SIZE):
            chunk_df = df.iloc[i:i + CHUNK_SIZE]
            chunk_data = [(index, row.to_dict()) for index, row in chunk_df.iterrows()]
            chunks.append(chunk_data)
        
        total_chunks = len(chunks)
        print(f"Created {total_chunks} chunks for processing")
        
        # Create chunk processing tasks
        from celery import chord
        
        chunk_tasks = [
            process_email_chunk.s(chunk_data, chunk_index, job_id, total_chunks)
            for chunk_index, chunk_data in enumerate(chunks)
        ]
        
        # Use chord to process all chunks and combine results
        callback = combine_chunk_results.s(job_id, total_rows)
        chord(chunk_tasks)(callback)
        
        return {
            "status": "STARTED",
            "total_rows": total_rows,
            "total_chunks": total_chunks,
            "chunk_size": CHUNK_SIZE
        }
        
    except Exception as e:
        print(f"Error starting spreadsheet processing: {str(e)}")
        update_status(job_id, "FAILURE", 0, 0)
        return {"status": "FAILURE", "error": str(e)}