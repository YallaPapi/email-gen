import os
import time
import pandas as pd
from celery import Celery
from openai import OpenAI

# Create Celery app
celery_app = Celery('tasks')
celery_app.config_from_object('celeryconfig')

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def rate_limited_api_call():
    """Rate limiting between API calls"""
    time.sleep(0.5)

def simple_clean(email_text):
    """Simple email cleaning - remove subject lines and signatures only"""
    import re
    
    # Remove subject lines
    email_text = re.sub(r'^Subject:.*?\n', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Split by lines and find the greeting
    lines = email_text.split('\n')
    start_idx = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Hey '):
            start_idx = i
            break
    
    # Take from greeting onwards
    lines = lines[start_idx:]
    
    # Remove only signature lines at the END
    cleaned_lines = []
    signature_started = False
    
    for line in lines:
        line = line.strip()
        
        # If we hit a signature line, mark it and skip the rest
        if any(sig in line for sig in ['Best regards', 'Looking forward', '[Your Name]', '[Your Company]', '[Your Title]', '[Your Contact']):
            signature_started = True
            continue
            
        # If signature hasn't started, keep the line
        if not signature_started and line:
            cleaned_lines.append(line)
    
    return '\n\n'.join(cleaned_lines)

@celery_app.task(bind=True, max_retries=3, ignore_result=False)
def process_single_row(self, row_data, row_index):
    """Process a single row - SIMPLE VERSION"""
    try:
        print(f"Processing row {row_index}")
        
        # Extract basic data using correct field names
        first_name = row_data.get('first_name', 'there')
        organization_name = row_data.get('organization_name', '')
        industry = row_data.get('industry', '')
        title = row_data.get('title', '')
        city = row_data.get('city', '')
        organization_short_description = row_data.get('organization_short_description', '')
        
        # Concise structure system prompt
        system_prompt = """You are writing a short, casual cold email. Follow this structure but vary the language:

STRUCTURE:
1. Greeting - "Hey [name]" 
2. Observation - brief acknowledgment of their role/company
3. Introduction - "I/We do AI automation"
4. Value proposition - 2-3 specific ways AI can help them 
5. CTA + Fallback - "If you're interested, let's set up a call. If not, all good."

KEEP IT MODERATE LENGTH - 100-130 words total. Be conversational but not verbose. Add some personality but stay direct."""
        
        # Updated user prompt with correct field names
        prospect_info = '\n'.join([f"{col}: {val}" for col, val in row_data.items()])
        
        user_prompt = f"""
Contact Information:
First Name: {first_name}
Organization: {organization_name}
Industry: {industry}
Title: {title}
City: {city}
Description: {organization_short_description}

Write a SHORT cold email (60-80 words). Follow the structure:

1. Hey {first_name},
2. Brief observation about their role as {title} at {organization_name}
3. Mention you do AI automation  
4. List 2-3 ways AI helps: select 1-2 from (database reactivation via SMS, automated lead generation, custom chatbots) PLUS 1-2 industry-specific solutions for {industry}
5. End with: "If you're interested, let's set up a call. If not, all good."

TARGET 100-130 words. Add some conversational flair but don't ramble. Stick to the structure but make it feel human and personable.
"""
        
        rate_limited_api_call()
        
        # Generate email with original settings
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=200,
        )
        
        email_content = completion.choices[0].message.content.strip()
        
        # Simple cleaning
        email_content = simple_clean(email_content)
        
        return {
            "index": row_index,
            "row_data": row_data,
            "email": email_content,
            "status": "success"
        }
        
    except Exception as e:
        print(f"ERROR in row {row_index}: {str(e)}")
        return {
            "index": row_index,
            "row_data": row_data,
            "email": f"ERROR: {str(e)}",
            "status": "error"
        }

@celery_app.task(bind=True, max_retries=3, ignore_result=False)
def process_spreadsheet_task(self, file_path, job_id, mode="simple"):
    """Main task for processing spreadsheet - SIMPLE VERSION"""
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        results = []
        
        for index, row in df.iterrows():
            result = process_single_row(row.to_dict(), index)
            results.append(result)
        
        # Create results DataFrame
        flattened_results = []
        for result in results:
            flattened_row = result["row_data"].copy()
            flattened_row["email"] = result.get("email", "")
            flattened_row["status"] = result.get("status", "")
            flattened_results.append(flattened_row)
        
        results_df = pd.DataFrame(flattened_results)
        
        # Save results
        output_file = f"uploads/result_{job_id}.xlsx"
        results_df.to_excel(output_file, index=False)
        
        return {
            'status': 'SUCCESS',
            'output_file': output_file
        }
        
    except Exception as e:
        return {
            'status': 'FAILURE', 
            'error': str(e)
        }