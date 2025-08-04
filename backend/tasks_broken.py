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
    """NUCLEAR CLEANING - REMOVE EVERYTHING UNWANTED WITH REGEX"""
    import re
    
    # Step 1: Remove subject lines completely (any line starting with subject)
    email_text = re.sub(r'^Subject:.*$', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    email_text = re.sub(r'^subject:.*$', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    
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
    
    # Step 3: Remove signature patterns aggressively
    signature_patterns = [
        r'^\s*Cheers!?\s*$',
        r'^\s*Best!?\s*$', 
        r'^\s*Thanks!?\s*$',
        r'^\s*Regards?\s*$',
        r'^\s*Sincerely\s*$',
        r'^\s*\[Your Name\]\s*$',
        r'^\s*\[.*\]\s*$',
        r'^\s*Yours truly\s*$',
        r'^\s*Warm regards\s*$'
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
    
    # Step 4: Remove trailing empty lines and signature remnants
    while filtered_lines and (not filtered_lines[-1].strip() or 
                              filtered_lines[-1].strip().lower() in ['cheers', 'best', 'thanks', 'regards']):
        filtered_lines.pop()
    
    # Step 5: Join and aggressive final cleanup
    result = '\n'.join(filtered_lines)
    
    # Nuclear regex cleanup - remove any remaining unwanted patterns
    result = re.sub(r'Subject:.*?\n', '', result, flags=re.IGNORECASE)
    result = re.sub(r'Cheers!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Best!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Thanks!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Regards[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'\[Your Name\][,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'\[.*\][,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up multiple newlines and trailing whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    result = result.strip()
    
    return result

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
        
        # INITIAL EMAIL - ORIGINAL WORKING PROMPT
        rate_limited_api_call()
        
        completion_initial = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in \"AI automation\" TO that prospect. It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company. Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley."},
                {"role": "user", "content": f"Write a natural, conversational cold email using this contact information:\n---\n{prospect_info}\n---\nWrite like you're a real person reaching out - natural, authentic, non-promotional tone.\n\nHere are 5 examples of the style and variety I want:\n\nExample 1:\nHey Mike,\nHope you're doing well over at Lakeside Inn. I work with AI automation and noticed your casino's potential for streamlining operations. With your focus on customer experience, AI could help optimize processes and drive growth. If that sounds good, let's get on a call. If not, all good. 😊\n\nExample 2:\nSarah, hope you're well!\nI specialize in AI automation and came across TechCorp's recent expansion - impressive stuff! I've been helping similar companies automate their workflows and thought there might be some cool ways we could help scale your operations more efficiently. If you're interested, let's set up a call. If not, all good! 🙂\n\nExample 3:\nHi David,\nHope things are going well at your firm. I work with AI automation and noticed you're handling a lot of client data - there might be some smart ways to streamline that process and save your team time. If that is something you'd like to hear more about, let's schedule a quick call so we can learn more about how we can help you. If not, all good! 😊\n\nExample 4:\nHey Lisa,\nHope you're crushing it in Austin! I work with AI automation and saw that InnovateTech is doing some really cool stuff in the software space. I've helped similar companies automate their lead generation processes with some pretty solid results. If that sounds good, let's get on a call. If not, all good! 😊\n\nExample 5:\nTom, hope you're well!\nI work with AI automation and couldn't help but notice the growth at CloudSolutions. Your approach to customer service is impressive! I've been working with companies in similar spaces to streamline their support processes using AI chatbots. If you're interested, let's set up a call. If not, all good! 🙂\n\nKey guidelines:\n- Start casually: \"Hey {first_name}\", \"Hi {first_name}\", \"{first_name}, hope you're well\"\n- Mention you work with AI automation in a casual way.\n- Reference their specific situation when possible.\n- Keep it conversational and authentic.\n- End with natural call-to-action like the examples, then \"if not\" + reassurance (all good/no problem/totally fine)\n- Use proper spacing with blank lines between paragraphs for readability.\n- NO signatures, names, or formal closings.\n- 50-70 words max.\nMake each email sound completely different - vary greetings, structure, tone, and phrasing naturally."}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        initial_email = nuclear_clean_email(completion_initial.choices[0].message.content.strip())
        
        # FOLLOW-UP 1 - ORIGINAL WORKING PROMPT
        rate_limited_api_call()
        
        completion_followup1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI automation expert. Write ONLY the email body text with no subject line, no signatures, no names, no formal closings. Intelligently analyze the prospect's industry and recommend specific AI services. Think like a business consultant. Be specific and industry-relevant, not generic. Show you understand their industry. Be conversational and authentic. CRITICAL: Do not include subject lines, signatures, \"Best,\" \"Sincerely,\" or any names."},
                {"role": "user", "content": f"You are an expert AI business consultant. Based on the following company data, identify the most pressing business challenge a company in the {industry} sector like {company_name} would face. Then, propose a specific, high-value AI solution (from our services: AI Chatbots, Automated Lead Gen, Database Reactivation) that directly solves that challenge. Frame it as a unique, tangible benefit. Do not be generic.\n\nHere are 5 examples of the industry-specific, consultative approach I want:\n\nExample 1 (Gambling/Casino):\nHey Mike, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nIn the gambling & casino sector, a key challenge is maximizing customer engagement and retention. Our AI Chatbots can enhance customer interactions, provide personalized recommendations, and address queries instantly, leading to improved satisfaction and loyalty.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 2 (Professional Services):\nHey Sarah, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nFor companies in professional services like yours, client database management can be overwhelming. Our Database Reactivation service uses AI to analyze dormant contacts and re-engage them with personalized outreach, turning cold leads into warm opportunities.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 3 (Healthcare):\nHey David, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nIn healthcare, patient communication and appointment management are critical pain points. Our AI Chatbots can handle appointment scheduling, send medication reminders, and answer common patient questions 24/7, reducing staff workload while improving patient satisfaction.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 4 (Real Estate):\nHey Lisa, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nIn real estate, lead qualification and follow-up are massive time drains. Our Automated Lead Gen system can instantly qualify prospects, schedule viewings, and nurture leads with personalized property recommendations, letting you focus on closing deals.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 5 (E-commerce):\nHey Tom, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nFor e-commerce companies, cart abandonment and customer support volume are huge challenges. Our AI Chatbots can recover abandoned carts with personalized offers and handle customer inquiries instantly, boosting conversions and reducing support costs.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nCompany: {company_name}\nIndustry: {industry}\nContact: {first_name}\n\nWrite a follow-up email that shows you understand their industry challenges and offer a specific AI solution that would genuinely help their business.\n\nStart with: \"Hey {first_name}, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\"\n\nEnd with: \"Happy to hop on a call if this sounds useful - if not, all good!\"\n\n60-80 words. NO signatures. NO subject lines. NO names like \"Best\" or \"Sincerely\". ONLY the email body text."}
            ],
            temperature=0.7,
            max_tokens=150,
        )
        followup_1_email = nuclear_clean_email(completion_followup1.choices[0].message.content.strip())
        
        # FOLLOW-UP 2 - ORIGINAL WORKING PROMPT
        rate_limited_api_call()
        
        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are writing a final follow-up email. Follow the exact format provided. Add humor and personality. NO signatures."},
                {"role": "user", "content": f"Write a final follow-up email to {first_name} at {company_name}.\n\nHere are 5 examples of the humorous, light-hearted style I want:\n\nExample 1:\nMike, one more try?\nIf I don't hear back, I'll assume you've found your automation superhero elsewhere and I'll let you focus on more exciting things than emails. You probably deserve a break from the grind anyway!\nP.S. If you're secretly training ninjas to handle your operations, just let me know.\n\nExample 2:\nSarah, one more try?\nI'll take the hint if you don't respond - no hard feelings! You're probably swamped with a million other priorities anyway. I'll assume you've got everything handled like a boss.\nP.S. If you ever need a digital sidekick, you know where to find me.\n\nExample 3:\nDavid, one more try?\nIf silence is your answer, I totally get it. You're probably drowning in client work and don't need another vendor bothering you. I'll bow out gracefully!\nP.S. If you change your mind, I promise to keep the follow-ups to a minimum.\n\nExample 4:\nLisa, one more try?\nNo response probably means you're too busy conquering the business world to deal with random emails. I respect that! I'll assume you've got everything under control.\nP.S. If you ever need someone to help automate world domination, I'm your person.\n\nExample 5:\nTom, one more try?\nI'll take the hint and stop filling up your inbox. You're probably too busy running an amazing company to chat with every AI automation person who reaches out!\nP.S. If you're secretly a robot yourself, my services might be redundant anyway.\n\nStart with: \"{first_name}, one more try?\"\n\nSay you'll assume they're not interested if you don't hear back and will leave them alone. Add some humor like \"you probably deserve a break from the grind.\"\n\nEnd with a short playful P.S.\n\n50-70 words. NO signatures."}
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

Write a casual email with variety - don't be boilerplate. Here are 3 examples:

Example 1:
Hey Mike,
Hope you're doing well over at Lakeside Inn. I work with AI automation and noticed your casino's potential for streamlining operations. With your focus on customer experience, AI could help optimize processes and drive growth. If that sounds good, let's get on a call. If not, all good.

Example 2:
Hi Sarah,
I work with AI automation and help companies like TechCorp automate their workflows. Saw your recent expansion and thought there might be some cool ways we could help scale your operations more efficiently. If that sounds good, let's get on a call. If not, all good.

Example 3:
Hey David,
Hope things are going well at your firm. I specialize in AI automation and noticed you're handling a lot of client data - there might be some smart ways to streamline that process. If that sounds good, let's get on a call. If not, all good.

Now write YOUR version for {first_name} at {company_name}. Make it different from the examples - vary the greeting, structure, and approach naturally.

50-70 words total. Just the body text."""

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write ONLY the email body text. DO NOT write any subject line. DO NOT start with 'Subject:'. DO NOT include signatures or names. Just write the email content starting with the greeting."},
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
        
        # INITIAL EMAIL - ORIGINAL WORKING PROMPT
        rate_limited_api_call()
        
        completion_initial = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in \"AI automation\" TO that prospect. It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company. Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley."},
                {"role": "user", "content": f"Write a natural, conversational cold email using this contact information:\n---\n{prospect_info}\n---\nWrite like you're a real person reaching out - natural, authentic, non-promotional tone.\n\nHere are 5 examples of the style and variety I want:\n\nExample 1:\nHey Mike,\nHope you're doing well over at Lakeside Inn. I work with AI automation and noticed your casino's potential for streamlining operations. With your focus on customer experience, AI could help optimize processes and drive growth. If that sounds good, let's get on a call. If not, all good. 😊\n\nExample 2:\nSarah, hope you're well!\nI specialize in AI automation and came across TechCorp's recent expansion - impressive stuff! I've been helping similar companies automate their workflows and thought there might be some cool ways we could help scale your operations more efficiently. If you're interested, let's set up a call. If not, all good! 🙂\n\nExample 3:\nHi David,\nHope things are going well at your firm. I work with AI automation and noticed you're handling a lot of client data - there might be some smart ways to streamline that process and save your team time. If that is something you'd like to hear more about, let's schedule a quick call so we can learn more about how we can help you. If not, all good! 😊\n\nExample 4:\nHey Lisa,\nHope you're crushing it in Austin! I work with AI automation and saw that InnovateTech is doing some really cool stuff in the software space. I've helped similar companies automate their lead generation processes with some pretty solid results. If that sounds good, let's get on a call. If not, all good! 😊\n\nExample 5:\nTom, hope you're well!\nI work with AI automation and couldn't help but notice the growth at CloudSolutions. Your approach to customer service is impressive! I've been working with companies in similar spaces to streamline their support processes using AI chatbots. If you're interested, let's set up a call. If not, all good! 🙂\n\nKey guidelines:\n- Start casually: \"Hey {first_name}\", \"Hi {first_name}\", \"{first_name}, hope you're well\"\n- Mention you work with AI automation in a casual way.\n- Reference their specific situation when possible.\n- Keep it conversational and authentic.\n- End with natural call-to-action like the examples, then \"if not\" + reassurance (all good/no problem/totally fine)\n- Use proper spacing with blank lines between paragraphs for readability.\n- NO signatures, names, or formal closings.\n- 50-70 words max.\nMake each email sound completely different - vary greetings, structure, tone, and phrasing naturally."}
            ],
            temperature=0.8,
            max_tokens=150,
        )
        initial_email = nuclear_clean_email(completion_initial.choices[0].message.content.strip())
        
        # FOLLOW-UP 1 - ORIGINAL WORKING PROMPT
        rate_limited_api_call()
        
        completion_followup1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI automation expert. Write ONLY the email body text with no subject line, no signatures, no names, no formal closings. Intelligently analyze the prospect's industry and recommend specific AI services. Think like a business consultant. Be specific and industry-relevant, not generic. Show you understand their industry. Be conversational and authentic. CRITICAL: Do not include subject lines, signatures, \"Best,\" \"Sincerely,\" or any names."},
                {"role": "user", "content": f"You are an expert AI business consultant. Based on the following company data, identify the most pressing business challenge a company in the {industry} sector like {company_name} would face. Then, propose a specific, high-value AI solution (from our services: AI Chatbots, Automated Lead Gen, Database Reactivation) that directly solves that challenge. Frame it as a unique, tangible benefit. Do not be generic.\n\nHere are 5 examples of the industry-specific, consultative approach I want:\n\nExample 1 (Gambling/Casino):\nHey Mike, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nIn the gambling & casino sector, a key challenge is maximizing customer engagement and retention. Our AI Chatbots can enhance customer interactions, provide personalized recommendations, and address queries instantly, leading to improved satisfaction and loyalty.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 2 (Professional Services):\nHey Sarah, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nFor companies in professional services like yours, client database management can be overwhelming. Our Database Reactivation service uses AI to analyze dormant contacts and re-engage them with personalized outreach, turning cold leads into warm opportunities.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 3 (Healthcare):\nHey David, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nIn healthcare, patient communication and appointment management are critical pain points. Our AI Chatbots can handle appointment scheduling, send medication reminders, and answer common patient questions 24/7, reducing staff workload while improving patient satisfaction.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 4 (Real Estate):\nHey Lisa, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nIn real estate, lead qualification and follow-up are massive time drains. Our Automated Lead Gen system can instantly qualify prospects, schedule viewings, and nurture leads with personalized property recommendations, letting you focus on closing deals.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nExample 5 (E-commerce):\nHey Tom, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\nFor e-commerce companies, cart abandonment and customer support volume are huge challenges. Our AI Chatbots can recover abandoned carts with personalized offers and handle customer inquiries instantly, boosting conversions and reducing support costs.\nHappy to hop on a call if this sounds useful - if not, all good!\n\nCompany: {company_name}\nIndustry: {industry}\nContact: {first_name}\n\nWrite a follow-up email that shows you understand their industry challenges and offer a specific AI solution that would genuinely help their business.\n\nStart with: \"Hey {first_name}, hope you're good. Just wanted to shoot you this quick email with a little more info about how we would be able to help.\"\n\nEnd with: \"Happy to hop on a call if this sounds useful - if not, all good!\"\n\n60-80 words. NO signatures. NO subject lines. NO names like \"Best\" or \"Sincerely\". ONLY the email body text."}
            ],
            temperature=0.7,
            max_tokens=150,
        )
        followup_1_email = nuclear_clean_email(completion_followup1.choices[0].message.content.strip())
        
        # FOLLOW-UP 2 - ORIGINAL WORKING PROMPT
        rate_limited_api_call()
        
        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are writing a final follow-up email. Follow the exact format provided. Add humor and personality. NO signatures."},
                {"role": "user", "content": f"Write a final follow-up email to {first_name} at {company_name}.\n\nHere are 5 examples of the humorous, light-hearted style I want:\n\nExample 1:\nMike, one more try?\nIf I don't hear back, I'll assume you've found your automation superhero elsewhere and I'll let you focus on more exciting things than emails. You probably deserve a break from the grind anyway!\nP.S. If you're secretly training ninjas to handle your operations, just let me know.\n\nExample 2:\nSarah, one more try?\nI'll take the hint if you don't respond - no hard feelings! You're probably swamped with a million other priorities anyway. I'll assume you've got everything handled like a boss.\nP.S. If you ever need a digital sidekick, you know where to find me.\n\nExample 3:\nDavid, one more try?\nIf silence is your answer, I totally get it. You're probably drowning in client work and don't need another vendor bothering you. I'll bow out gracefully!\nP.S. If you change your mind, I promise to keep the follow-ups to a minimum.\n\nExample 4:\nLisa, one more try?\nNo response probably means you're too busy conquering the business world to deal with random emails. I respect that! I'll assume you've got everything under control.\nP.S. If you ever need someone to help automate world domination, I'm your person.\n\nExample 5:\nTom, one more try?\nI'll take the hint and stop filling up your inbox. You're probably too busy running an amazing company to chat with every AI automation person who reaches out!\nP.S. If you're secretly a robot yourself, my services might be redundant anyway.\n\nStart with: \"{first_name}, one more try?\"\n\nSay you'll assume they're not interested if you don't hear back and will leave them alone. Add some humor like \"you probably deserve a break from the grind.\"\n\nEnd with a short playful P.S.\n\n50-70 words. NO signatures."}
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
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an AI assistant writing a cold email. The user will provide you with information about a prospect. Your job is to write a short, casual email FROM a person who works in \"AI automation\" TO that prospect. It is critical that you understand this role. You are the sender. The prospect information is for the recipient. Do not get confused and act as if you work for the prospect's company. Follow all formatting rules from the user, especially the negative constraints about what NOT to include. The required output format is: Greeting\\n\\nMain Content\\n\\nCTA\\n\\nFallback with smiley."},
                {"role": "user", "content": f"Write a natural, conversational cold email using this contact information:\n---\n{prospect_info}\n---\nWrite like you're a real person reaching out - natural, authentic, non-promotional tone.\n\nHere are 5 examples of the style and variety I want:\n\nExample 1:\nHey Mike,\nHope you're doing well over at Lakeside Inn. I work with AI automation and noticed your casino's potential for streamlining operations. With your focus on customer experience, AI could help optimize processes and drive growth. If that sounds good, let's get on a call. If not, all good. 😊\n\nExample 2:\nSarah, hope you're well!\nI specialize in AI automation and came across TechCorp's recent expansion - impressive stuff! I've been helping similar companies automate their workflows and thought there might be some cool ways we could help scale your operations more efficiently. If you're interested, let's set up a call. If not, all good! 🙂\n\nExample 3:\nHi David,\nHope things are going well at your firm. I work with AI automation and noticed you're handling a lot of client data - there might be some smart ways to streamline that process and save your team time. If that is something you'd like to hear more about, let's schedule a quick call so we can learn more about how we can help you. If not, all good! 😊\n\nExample 4:\nHey Lisa,\nHope you're crushing it in Austin! I work with AI automation and saw that InnovateTech is doing some really cool stuff in the software space. I've helped similar companies automate their lead generation processes with some pretty solid results. If that sounds good, let's get on a call. If not, all good! 😊\n\nExample 5:\nTom, hope you're well!\nI work with AI automation and couldn't help but notice the growth at CloudSolutions. Your approach to customer service is impressive! I've been working with companies in similar spaces to streamline their support processes using AI chatbots. If you're interested, let's set up a call. If not, all good! 🙂\n\nKey guidelines:\n- Start casually: \"Hey {first_name}\", \"Hi {first_name}\", \"{first_name}, hope you're well\"\n- Mention you work with AI automation in a casual way.\n- Reference their specific situation when possible.\n- Keep it conversational and authentic.\n- End with natural call-to-action like the examples, then \"if not\" + reassurance (all good/no problem/totally fine)\n- Use proper spacing with blank lines between paragraphs for readability.\n- NO signatures, names, or formal closings.\n- 50-70 words max.\nMake each email sound completely different - vary greetings, structure, tone, and phrasing naturally."}
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