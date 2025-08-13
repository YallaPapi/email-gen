"""
Test the improved email format with better quality
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import hashlib
import random

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_rewrite_instructions(seed_value):
    """Generate randomized rewrite instructions for variation"""
    random.seed(seed_value)
    
    instruction_type = random.randint(0, 3)
    
    if instruction_type == 0:
        # Slight variations on standard format
        return f"""Rewrite this email keeping the same professional structure but change:
- Opening: {random.choice([
    'Hi [name], I noticed [company]...',
    'Hey [name], saw that [company]...',
    '[Name], I see [company] is in...',
    'Hi [name], [company] being in [industry]...'
])}
- Introduce problems: {random.choice([
    'probably deals with...',
    'likely faces challenges like...',
    'might struggle with...',
    'probably encounters...'
])}
- List 3 AI solutions clearly as {random.choice(['bullets (•)', 'dashes (-)', 'numbers (1,2,3)'])}
- Closing: {random.choice([
    'Interested in learning more? Let\'s chat. If not, no worries!',
    'Want to explore how this could help? Quick call? If not, all good.',
    'Sound useful? Happy to discuss. Otherwise, no problem!',
    'Think this could help? Let me know. If not, totally fine!'
])}"""
    
    elif instruction_type == 1:
        # Slightly more direct version
        return f"""Rewrite more directly but keep professional:
- Opening: {random.choice([
    '[Name], quick question - [company] probably deals with...',
    'Hi [name], [company] in [industry] likely faces...',
    '[Name] - Know [company] struggles with...'
])}
- List the problems briefly, then say "We help with:"
- 3 AI solutions as {random.choice(['short bullets', 'quick points', 'brief list'])}:
  • Keep each solution under 10 words
  • Be specific to their industry
  • One must be lead gen or chatbots
- Closing: {random.choice([
    'Worth a quick chat? Let me know.',
    'Interested? Happy to show you how. If not, no worries.',
    'Make sense? Quick call this week?',
    'Sound helpful? Let\'s connect. Or not - your call.'
])}"""
    
    elif instruction_type == 2:
        # Helpful/consultative approach
        return f"""Rewrite with helpful tone but same structure:
- Opening: {random.choice([
    'Hi [name], I work with [industry] companies like [company]...',
    'Hey [name], helping [industry] businesses like [company]...',
    '[Name], I noticed [company] is in [industry]. We help similar companies...'
])}
- Mention problems: "Most face challenges with [list 2-3 problems]"
- Transition: {random.choice([
    'Our AI solutions help with:',
    'We address these with:',
    'Here\'s how AI can help:'
])}
- List 3 solutions as {random.choice(['bullets', 'dashes', 'numbers'])}
- Closing: {random.choice([
    'Happy to share how this works for others in [industry]. Interested?',
    'Can show you what we\'ve done for similar companies. Worth discussing?',
    'Would love to explore if this fits [company]. Quick chat?',
    'Let me know if you\'d like to learn more. No pressure!'
])}"""
    
    else:
        # Natural but professional
        return f"""Rewrite naturally but keep it professional:
- Opening: {random.choice([
    'Hi [name], saw [company] works in [industry]...',
    'Hey [name], I noticed [company] is a [industry] business...',
    '[Name], looking at [company], I imagine you deal with...'
])}
- Problems section: {random.choice([
    'I imagine you face [list problems]',
    'You probably deal with [list problems]',
    'Common challenges I see: [list problems]'
])}
- Solutions intro: {random.choice([
    'We\'ve built AI tools that help:',
    'Our AI solutions address these:',
    'Here\'s what we offer:'
])}
- List 3 solutions clearly
- Closing: {random.choice([
    'If this sounds useful, let\'s chat. If not, no worries at all!',
    'Interested? Love to show you. Not interested? Totally understand.',
    'Want to learn more? Happy to explain. Otherwise, all good!',
    'Think this could help [company]? Let me know either way.'
])}"""

def generate_email(first_name, company, industry, index=0):
    """Generate email with improved format"""
    
    # Create unique hash
    unique_string = f"{first_name}{company}{industry}{index}"
    hash_seed = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
    
    # Base prompt - structured format
    base_system_prompt = f"""You are writing a cold email to someone in the {industry} industry.

Write a professional but friendly email that:
1. Opens with Hi [name] and mentions their company
2. States that companies in {industry} often deal with [2-3 specific problems]
3. Says "We help with:" and lists exactly 3 AI solutions:
   - ONE must be "AI lead generation" or "customer service chatbots"
   - The other 2 must be specific to {industry} problems
4. Ends with a soft CTA like "Interested? Let's chat. If not, no worries!"

Keep it 80-100 words. Be specific to {industry}, not generic."""

    base_user_prompt = f"""Write a cold email to:
Name: {first_name}
Company: {company}
Industry: {industry}"""

    try:
        # Generate base
        completion1 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": base_system_prompt},
                {"role": "user", "content": base_user_prompt}
            ],
            temperature=0.7,
            max_tokens=120
        )
        base_email = completion1.choices[0].message.content.strip()
        
        # Rewrite for variation
        rewrite_instructions = generate_rewrite_instructions(hash_seed)
        
        rewrite_prompt = f"""Original email:
{base_email}

{rewrite_instructions}

Keep all 3 AI solutions but present them with slight variations in wording."""

        completion2 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": rewrite_prompt}
            ],
            temperature=0.8,
            max_tokens=120
        )
        final_email = completion2.choices[0].message.content.strip()
        
        return base_email, final_email, hash_seed
        
    except Exception as e:
        return None, None, str(e)

def main():
    print("="*70)
    print("IMPROVED EMAIL FORMAT TEST")
    print("="*70)
    
    # Test with same industry to show variation
    test_cases = [
        {"first_name": "Mike", "company": "FASTSIGNS", "industry": "printing"},
        {"first_name": "Sarah", "company": "PrintPro", "industry": "printing"},
        {"first_name": "John", "company": "QuickPrint", "industry": "printing"},
    ]
    
    print("\nGenerating 3 emails for printing industry to show variation...")
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['first_name']} at {test['company']}")
        print("="*70)
        
        base, final, seed = generate_email(
            test["first_name"],
            test["company"],
            test["industry"],
            i
        )
        
        if base and final:
            print(f"\nHash Seed: {seed}")
            print("\nBASE EMAIL:")
            print("-"*40)
            print(base)
            print("\nFINAL EMAIL (After Variation):")
            print("-"*40)
            print(final)
        else:
            print(f"Error: {seed}")
    
    print("\n" + "="*70)
    print("KEY IMPROVEMENTS:")
    print("="*70)
    print("1. Consistent professional format")
    print("2. Clear structure maintained")
    print("3. Variation in wording but not quality")
    print("4. Industry-specific solutions")
    print("5. Proper greeting and closing")

if __name__ == "__main__":
    main()