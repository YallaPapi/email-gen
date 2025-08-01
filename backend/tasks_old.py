import os
import time
import pandas as pd
from celery import Celery, group
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)
celery_app.config_from_object('celeryconfig')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def update_status(job_id, status, progress, total):
    with open(f"uploads/{job_id}_status.txt", "w") as f:
        f.write(f"{status},{progress},{total}")

@celery_app.task(bind=True, max_retries=5)
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
- End with if-then call CTA + "if not, all good/no worries/totally fine" with a smiley.
- Use proper spacing with blank lines between paragraphs for readability.
- NO signatures, names, or formal closings.
- 50-70 words max.
Make each email sound completely different - vary greetings, structure, tone, and phrasing naturally.
"""
        
        system_prompt = """
You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in "AI automation" TO that prospect.
It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company.
Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley.
"""
        
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=200,
            )
        except Exception as api_error:
            if "429" in str(api_error):
                # Rate limit hit - retry with exponential backoff
                raise self.retry(exc=api_error, countdown=2 ** self.request.retries)
            raise
        email_text = completion.choices[0].message.content.strip()
        
        # Return the result with row index for ordering
        return {
            "index": row_index,
            "row_data": row_data,
            "email": email_text,
            "status": "success"
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

@celery_app.task
def combine_results(results, job_id, total_rows):
    """Combine all results into final Excel file"""
    try:
        # Sort results by index to maintain original order
        sorted_results = sorted(results, key=lambda x: x['index'])
        
        # Build final dataframe
        final_data = []
        for result in sorted_results:
            row = result['row_data'].copy()
            row['generated_email'] = result['email']
            final_data.append(row)
        
        # Save to Excel
        df = pd.DataFrame(final_data)
        output_file = f"uploads/result_{job_id}.xlsx"
        df.to_excel(output_file, index=False)
        
        # Update final status
        update_status(job_id, "SUCCESS", total_rows, total_rows)
        
        # Clean up Redis progress counter
        from celery import current_app
        current_app.backend.client.delete(f"progress_{job_id}")
        
        return {"status": "SUCCESS", "file": output_file}
        
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