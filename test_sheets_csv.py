"""
Test email generation with the actual test sheets CSV file
Shows the two-step process working with real lead data
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
import hashlib
import random
import time

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_rewrite_instructions(seed_value):
    """Generate randomized rewrite instructions for variation"""
    random.seed(seed_value)
    
    instruction_type = random.randint(0, 3)
    
    if instruction_type == 0:
        return f"""Rewrite this email with these requirements:
- {random.choice(['Casual', 'Friendly', 'Conversational', 'Relaxed'])} tone
- {random.choice(['Start with a question', 'Open with just their name', 'Begin with an observation'])}
- {random.choice(['Use numbered list', 'Use bullet points', 'Use natural paragraph flow'])} for solutions
- {random.choice(['End with soft CTA', 'Close with yes/no question', 'Finish with "chat soon?"'])}
- Make it {random.choice(['shorter', 'more concise', 'punchier'])}"""
    
    elif instruction_type == 1:
        return f"""Make this email {random.choice(['super direct', 'ultra-brief', 'straight to the point'])}:
- {random.choice(['Max 5 sentences total', 'Under 50 words', 'Bullet points only'])}
- {random.choice(['Cut all fluff', 'Remove pleasantries', 'Get straight to value'])}
- {random.choice(['One-line opener', 'Name-only greeting', 'Direct statement start'])}
- {random.choice(['Binary CTA (yes/no)', 'Single question close', 'Direct ask'])}"""
    
    elif instruction_type == 2:
        return f"""Rewrite using {random.choice(['storytelling', 'an example', 'results-first'])}:
- {random.choice(['Start with results we achieved', 'Open with client success', 'Lead with an example'])}
- {random.choice(['Show dont tell', 'Use specific numbers', 'Focus on ROI'])}
- {random.choice(['Conversational flow', 'Natural progression', 'Problem-solution format'])}
- Make it {random.choice(['relatable', 'tangible', 'concrete'])}"""
    
    else:
        return f"""Rewrite as {random.choice(['natural conversation', 'helpful message', 'friendly chat'])}:
- {random.choice(['Write like texting a colleague', 'Make it sound human', 'Keep it authentic'])}
- {random.choice(['Use their first name naturally', 'Reference their company casually'])}
- {random.choice(['Natural solution mentions', 'Organic value props', 'Conversational benefits'])}
- {random.choice(['Soft close', 'Gentle CTA', 'No-pressure ending'])}"""

def generate_two_step_email(row_data, row_index=0):
    """Generate email using two-step process"""
    
    # Extract fields matching what the system expects
    first_name = row_data.get('first_name', 'there')
    organization_name = row_data.get('organization_name', 'your company')
    industry = row_data.get('industry', 'your industry')
    org_description = row_data.get('organization_short_description', '')
    
    # Create unique hash for this recipient
    unique_string = f"{first_name}{organization_name}{industry}{row_index}"
    hash_seed = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
    
    # STEP 1: Generate base email
    base_system_prompt = f"""You are writing a cold email to someone in the {industry} industry.

TASK: Think about what specific problems the {industry} industry faces. Then provide exactly 3 AI-powered solutions.

REQUIREMENTS:
1. Identify real problems {industry} businesses face
2. Offer exactly 3 AI solutions
3. ONE must be either "AI lead generation" or "customer service chatbots"
4. The other 2 should be highly specific to {industry} problems

Keep it brief and conversational. Under 100 words."""

    base_user_prompt = f"""Write a cold email to:
Name: {first_name}
Company: {organization_name}
Industry: {industry}
Description: {org_description if org_description else 'N/A'}"""

    try:
        # Generate base email
        completion1 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": base_system_prompt},
                {"role": "user", "content": base_user_prompt}
            ],
            temperature=0.8,
            max_tokens=120
        )
        base_email = completion1.choices[0].message.content.strip()
        
        # STEP 2: Rewrite for variation
        rewrite_instructions = generate_rewrite_instructions(hash_seed)
        
        rewrite_prompt = f"""Take this email and rewrite it completely:

ORIGINAL EMAIL:
{base_email}

REWRITE INSTRUCTIONS:
{rewrite_instructions}

Keep all 3 AI solutions but present them differently."""

        completion2 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": rewrite_prompt}
            ],
            temperature=0.9,
            max_tokens=120
        )
        final_email = completion2.choices[0].message.content.strip()
        
        return {
            'first_name': first_name,
            'organization': organization_name,
            'industry': industry,
            'description': org_description[:50] + '...' if len(org_description) > 50 else org_description,
            'hash_seed': hash_seed,
            'email': final_email
        }
        
    except Exception as e:
        return {
            'first_name': first_name,
            'organization': organization_name,
            'error': str(e)
        }

def main():
    print("="*70)
    print("TEST SHEETS CSV - EMAIL GENERATION")
    print("="*70)
    
    # Load the CSV
    csv_file = "tests sheets - Sheet1.csv"
    
    try:
        df = pd.read_csv(csv_file)
        print(f"\nLoaded CSV with {len(df)} leads")
        print(f"Industries: {', '.join(df['industry'].unique())}")
        
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return
    
    print("\n" + "="*70)
    print("GENERATING EMAILS")
    print("="*70)
    
    results = []
    
    # Process each row
    for index, row in df.iterrows():
        lead_num = index + 1
        print(f"\n[{lead_num}/{len(df)}] Processing {row['first_name']} at {row['organization_name']}...")
        
        # Convert row to dict
        row_data = row.to_dict()
        
        # Generate email
        result = generate_two_step_email(row_data, index)
        results.append(result)
        
        # Rate limiting
        if index < len(df) - 1:
            time.sleep(1)
    
    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*70}")
        print(f"EMAIL {i}: {result['first_name']} at {result['organization']}")
        print(f"Industry: {result['industry']}")
        
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        else:
            if 'description' in result and result['description'] != 'N/A':
                print(f"Description: {result['description']}")
            print(f"Hash Seed: {result['hash_seed']}")
            print("-"*40)
            print(result['email'])
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    successful = len([r for r in results if 'email' in r])
    print(f"[OK] Generated {successful}/{len(results)} emails successfully")
    
    if successful > 0:
        print("\nIndustries processed:")
        industries = {}
        for r in results:
            if 'industry' in r:
                ind = r['industry']
                industries[ind] = industries.get(ind, 0) + 1
        
        for ind, count in industries.items():
            print(f"  - {ind}: {count} emails")
    
    # Save results to CSV
    output_file = "test_sheets_results.csv"
    output_data = []
    for r in results:
        if 'email' in r:
            output_data.append({
                'first_name': r['first_name'],
                'organization': r['organization'],
                'industry': r['industry'],
                'email': r['email']
            })
    
    if output_data:
        output_df = pd.DataFrame(output_data)
        output_df.to_csv(output_file, index=False)
        print(f"\n[OK] Results saved to {output_file}")

if __name__ == "__main__":
    main()