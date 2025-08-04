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
        
        # STEP 1: Generate initial email - USER'S EXACT PROMPT
        user_prompt_initial = f"""
Contact info:
---
{prospect_info}
---
Rules:
If the fields organization_short_description and industry have data in them, then use that data to create a personalized response that shows an understanding of the common problems in their industry. Then provide an example of how AI can help solve those problems. Use literal language. Make each email significantly personalized and vary your language. 

If those fields are blank, then examine organization_name and use your best judgement about the industry and type of business they are in. 

End all emails with a spun version of this:

If {{you're interested|that sounds good|you want more info}}, let's {{schedule|get on|set up}} a quick {{call|meeting|Zoom call}} and I {{will show you everything|can show you how it works|will show you the magic}}. If not, {{all good|no problem|no worries}}.

Keep it concise but sufficiently personalized
"""

        system_prompt_initial = """
You are writing a cold email. The user prompt contains special spintext formatting that you MUST process correctly.

SPINTEXT PROCESSING GUIDE:
Spintext appears as {{option1|option2|option3}} with curly brackets and options separated by vertical bars. This is NOT part of the email text - it's instructions for you to create variations. Here's exactly how to handle it:

1. IDENTIFY: Look for any text wrapped in double curly brackets {{ }}
2. EXTRACT: Find all options separated by vertical bars |
3. CHOOSE: Randomly select ONE option from each bracket group
4. REPLACE: Write the chosen option naturally in the email, removing ALL brackets and bars
5. VARY: Make different random choices each time you see spintext

EXAMPLE PROCESSING:
Input: "If {{you're interested|that sounds good|you want more info}}, let's {{schedule|get on|set up}} a quick {{call|meeting|Zoom call}}"

Possible outputs:
- "If you're interested, let's schedule a quick call"
- "If that sounds good, let's get on a meeting" 
- "If you want more info, let's set up a quick Zoom call"

CRITICAL RULES:
- NEVER write {{ }} brackets in your response
- NEVER write | vertical bars in your response  
- ALWAYS pick ONE option from each group
- ALWAYS make random selections to create variety
- The spintext creates natural language variations

Process ALL spintext in the user prompt this way. Write personalized emails using the contact information provided.
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
        
        # STEP 2: Generate follow-up 1 - USER'S EXACT PROMPT
        user_prompt_followup1 = f"""
Company: {company_name}
Contact: {first_name}

Tell the client you just wanted to send over a bit more info about how we can help. For example, it may look something like this:

Hey {first_name}, just {{thought I'd|wanted to}} {{send|shoot}} over {{some|a bit}} more {{info|information}} on {{how we work|how we can help you|what we can do to help you}} over at {company_name}.

Then give specific information on how our ai solutions can help. Here is a spintext example of how that would look:

– {{Custom AI chatbots|GPT-based automation|AI assistant creation}} - {company_name}'s {{knowledge base|unique knowledge}} {{fed to|wrapped in}} an {{AI|OpenAI}} chat interface
– {{Lead reactivation|Database follow-ups|Old lead outreach}} - {{AI-generated|AI-based}} {{text|SMS}} messages, {{designed|made}} to {{book appointments|make appointments}}
– {{Sales process automation|Automated follow-ups and scheduling|Automated lead generation}} - automate your entire {{lead|sales|selling}} cycle from {{"who?"|cold}} to {{"I'll take it"|ready to buy}}

End all emails with a spun version of this:

If {{you're interested|that sounds good|you want more info}}, let's {{schedule|get on|set up}} a quick {{call|meeting|Zoom call}} and I {{will show you everything|can show you how it works|will show you the magic}}. If not, {{all good|no problem|no worries}}.
"""
        
        system_prompt_followup1 = """
Write a follow-up email using the spintext format shown. 

CRITICAL: When you see {{option1|option2|option3}} anywhere in the user prompt, you MUST replace it with ONE randomly chosen option. Do NOT include the {{}} brackets in your response. The brackets are instructions for you, not part of the email text.

Do not add any extra closings or signatures beyond what the user prompt specifies.
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

End with: "If not, all good!" or "If not, no problem!"

50-70 words. NO signatures.
"""
        
        rate_limited_api_call()
        
        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are writing a final follow-up email. Follow the exact format provided. Add humor and personality. NO signatures. SPAM WORD RESTRICTIONS - NEVER use: 100% free, make money, earn extra cash, guaranteed, million dollars, free gift, financial freedom, risk-free, incredible deal, once in a lifetime, act now, click here, get it now, urgent, limited time, order now, while supplies last, do it today, take action, don't delete, no catch, no hidden fees, no credit check, meet singles, multi-level marketing, social security number, weight loss, this isn't spam, unsolicited, hidden charges, cheap, bonus, cash, discount, pre-approved, clearance, bargain, income, loans, rates."},
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
Write a personalized cold email using this contact information:
---
{prospect_info}
---

Start with "Hey [first_name]," and mention you work with AI automation. Reference their company and/or industry specifically. Keep it conversational and authentic. End with "If you're open to a chat, let me know - if not, all good."

NO signatures, names, or formal closings. 50-80 words max.
"""
        
        system_prompt = """
You are writing a personalized cold email. Write ONLY the email body text with NO subject line, NO signatures, NO names, NO formal closings.
Be specific about their company/industry. Be conversational and direct.
CRITICAL: Do not include "Subject:", "Best,", "Cheers,", "[Your Name]", or any signatures.
MANDATORY: End with EXACTLY "If you're open to a chat, let me know - if not, all good."
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
        
        # Save results - preserve original columns and add email columns
        if results:
            # Create a list to hold flattened results
            flattened_results = []
            
            for result in results:
                # Start with the original row data
                flattened_row = result["row_data"].copy()
                
                # Add the email columns and metadata
                if mode == "sequence":
                    flattened_row["initial_email"] = result.get("initial_email", "")
                    flattened_row["followup_1"] = result.get("followup_1", "")  
                    flattened_row["followup_2"] = result.get("followup_2", "")
                else:
                    flattened_row["generated_email"] = result.get("email", "")
                
                flattened_row["status"] = result.get("status", "")
                flattened_row["model_used"] = result.get("model_used", "")
                
                flattened_results.append(flattened_row)
            
            results_df = pd.DataFrame(flattened_results)
        else:
            results_df = pd.DataFrame()
            
        output_path = f"uploads/result_{job_id}.xlsx"
        results_df.to_excel(output_path, index=False)
        
        final_status = "SUCCESS" if failed_count == 0 else f"PARTIAL_{failed_count}_ERRORS"
        update_status(job_id, final_status, total_rows, total_rows)
        
        return {"status": final_status, "output_file": output_path}
        
    except Exception as e:
        update_status(job_id, "FAILURE", 0, 0)
        raise e