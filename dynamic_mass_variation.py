import random
import hashlib

def generate_mass_campaign_email(row_data, campaign_index):
    """
    Generate unique emails for mass campaigns using:
    1. Two-step generation: Base + Rewrite
    2. Dynamic prompting with randomized instructions
    3. Hash-based seeding for deterministic but unique outputs
    """
    
    first_name = row_data.get('first_name', 'there')
    company_name = row_data.get('organization_name', 'your company')
    industry = row_data.get('industry', '')
    org_description = row_data.get('organization_short_description', '')
    
    # Create unique seed from data + index
    unique_string = f"{company_name}{first_name}{campaign_index}"
    hash_seed = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
    random.seed(hash_seed)
    
    # STEP 1: Generate base email with industry-specific 3 solutions
    base_prompt = f"""
Write a cold email to {first_name} at {company_name} in {industry}.

Identify 3 problems {industry} faces. Offer 3 AI solutions:
- One MUST be lead generation or chatbots
- Two others specific to {industry}

{random.choice([
    'Keep it under 80 words.',
    'Be concise - 60-90 words max.',
    'Short and punchy - under 100 words.',
    'Get to the point fast - 70 words or less.'
])}

{random.choice([
    'End with a call to action.',
    'Close with next steps.',
    'Finish with a clear CTA.',
    'End asking for a response.'
])}"""
    
    # STEP 2: Rewrite instructions with heavy randomization
    rewrite_instructions = random.choice([
        # Instruction Set A - Tone variations
        f"""Rewrite this email with {random.choice(['casual', 'friendly', 'conversational', 'relaxed'])} tone.
{random.choice(['Start with', 'Open with', 'Begin with'])} {random.choice([
    'a question',
    'their first name only', 
    'a brief observation',
    'mentioning their company',
    'acknowledging their role'
])}.
{random.choice(['Use', 'Include', 'Add'])} {random.choice(['bullets', 'dashes', 'numbers', 'short paragraphs'])}.
End: "{random.choice([
    "Interested? Let's chat. If not, no worries.",
    "Worth a quick call? All good if not.",
    "Want to explore this? No pressure if not.",
    "Sound useful? Happy to explain. Or not - all good.",
    "Make sense? Can show you more. Otherwise, no problem."
])}" """,
        
        # Instruction Set B - Structure variations  
        f"""Restructure as {random.choice([
    'problem-solution format',
    'story/example approach',
    'direct value proposition',
    'question-answer style',
    'benefit-focused pitch'
])}.
{random.choice(['Mention', 'Reference', 'Include'])} {random.choice([
    f'how AI helps {industry}',
    'specific time/cost savings',
    'automation benefits',
    f'what other {industry} companies do',
    'efficiency improvements'
])}.
List solutions {random.choice(['as bullets', 'inline in sentences', 'as numbered points', 'in one paragraph'])}.
CTA: {random.choice([
    '"If this resonates, quick call? If not, all good."',
    '"Let me know if interested. No worries if not."',
    '"Worth discussing? Your call - no pressure."',
    '"Sound helpful? Chat soon? Or not - totally fine."'
])}""",

        # Instruction Set C - Length/style variations
        f"""Make this {random.choice(['shorter', 'punchier', 'more direct', 'super brief'])}.
{random.choice(['Cut', 'Remove', 'Eliminate'])} {random.choice(['fluff', 'extra words', 'unnecessary details', 'filler'])}.
{random.choice(['Lead with', 'Start with', 'Open with'])} {random.choice([
    'the value',
    'what you do',
    'their problem',
    'your solution',
    'a question'
])}.
3 solutions in {random.choice(['10 words each', 'one-liners', 'brief phrases', 'super short bullets'])}.
Close: "{random.choice([
    'Interested? = call. Not? = all good.',
    'Yes = we talk. No = no problem.',
    'Worth exploring? Let me know either way.',
    'Make sense? Quick chat or pass?',
    'Sound good? Up to you.'
])}" """,

        # Instruction Set D - Personality variations
        f"""{random.choice(['Add personality', 'Make it human', 'Sound more natural', 'Be more personable'])}.
{random.choice(['Acknowledge', 'Mention', 'Reference'])} {random.choice([
    f'their {industry} challenges',
    'what they probably deal with',
    'common industry pain points',
    'their daily struggles',
    f'running a {industry} business'
])}.
Present solutions {random.choice([
    'conversationally',
    'as helpful suggestions',
    'like friendly advice',
    'as possibilities',
    'as options to consider'
])}.
End naturally: "{random.choice([
    'If any of this helps, lets talk. Otherwise, all good!',
    'Could be useful? Happy to chat. Or not - your call.',
    'Think this could work? Quick call? No stress if not.',
    'Might be worth exploring? Let me know. Or dont - totally fine.'
])}" """
    ])
    
    # Additional variation layer - word substitutions
    word_variations = {
        'help': random.choice(['help', 'assist', 'support', 'work with']),
        'AI': random.choice(['AI', 'automation', 'AI automation', 'smart tools']),
        'solutions': random.choice(['solutions', 'tools', 'systems', 'approaches']),
        'business': random.choice(['business', 'company', 'organization', 'operation']),
        'quick': random.choice(['quick', 'brief', 'short', '15-min']),
        'call': random.choice(['call', 'chat', 'conversation', 'zoom']),
        'interested': random.choice(['interested', 'curious', 'want to explore', 'intrigued']),
        'curious': random.choice(['curious', 'interested', 'intrigued', 'wondering'])
    }
    
    # Simulate the two-step process
    # In production, this would be:
    # 1. First OpenAI call with base_prompt
    # 2. Second OpenAI call with rewrite_instructions
    
    # For demonstration, showing what the variation would look like:
    variation_style = hash_seed % 10
    
    if variation_style == 0:
        email = f"""{first_name}, quick question -

Running {company_name} in {industry}, you probably fight with manual processes daily.

Three AI {word_variations['solutions']} that could {word_variations['help']}:
• Lead generation on autopilot
• {industry}-specific workflow automation  
• Customer service chatbots

{word_variations['interested'].capitalize()}? {word_variations['quick'].capitalize()} {word_variations['call']}. Not? All good."""

    elif variation_style == 1:
        email = f"""Hey {first_name},

Been thinking about {company_name}. {industry} companies like yours usually struggle with efficiency.

We've built:
- AI prospecting that never stops
- Automated {industry} operations
- 24/7 support bots

Worth exploring? Let me know either way."""

    elif variation_style == 2:
        email = f"""{first_name} -

{company_name} could save 10+ hours/week with {word_variations['AI']}.

Specifically:
1. Automated lead finding
2. {industry} process optimization
3. Instant customer support

Make sense? = {word_variations['call']}. Not? = no problem."""

    elif variation_style == 3:
        email = f"""Hi {first_name}, hope all's well.

I {word_variations['help']} {industry} businesses automate the boring stuff. Finding leads automatically, handling routine tasks, answering customer questions instantly.

Think this could work for {company_name}?

{word_variations['interested'].capitalize()}? Happy to explain. Or not - totally fine."""

    elif variation_style == 4:
        email = f"""{first_name},

Just helped another {industry} company cut manual work by 60%.

The formula: smart lead generation + operational {word_variations['AI']} + customer chatbots.

Could do similar for {company_name}. Worth a {word_variations['quick']} {word_variations['call']}? No pressure if not."""

    elif variation_style == 5:
        email = f"""Hey {first_name} -

{industry} + AI = less hassle.

Three ways we help:
- Leads come to you (not vice versa)
- Repetitive tasks disappear
- Customers get instant answers

Sound useful? Let's talk. Or don't - all good!"""

    elif variation_style == 6:
        email = f"""{first_name}, real quick:

What if {company_name} had AI handling lead gen, {industry} operations, and customer service?

That's what we do.

{word_variations['curious'].capitalize()}? = 15 min chat.
Not? = I'll leave you be."""

    elif variation_style == 7:
        email = f"""Hi {first_name},

Noticed {company_name}. With {industry}, I bet customer acquisition and operations eat up your time.

Our {word_variations['AI']} handles:
• New lead generation
• Daily task automation
• Customer inquiries

If this resonates, {word_variations['quick']} {word_variations['call']}? If not, no worries."""

    elif variation_style == 8:
        email = f"""{first_name} -

Three {industry} problems. Three AI {word_variations['solutions']}.

Problems: Manual prospecting, repetitive tasks, customer support overload.
Solutions: AI lead gen, workflow automation, smart chatbots.

Worth discussing? Your call - no pressure."""

    else:
        email = f"""Hey {first_name},

I work with {industry} companies on {word_variations['AI']} automation. Nothing complex - just tools that find customers, automate workflows, and handle support.

Could {word_variations['help']} {company_name} save time and grow faster.

{word_variations['interested'].capitalize()}? Let's connect. Not interested? Honestly all good!"""
    
    return email

def test_mass_variation():
    """Test 10 emails for same company to show variation"""
    
    print("=" * 60)
    print("MASS CAMPAIGN VARIATION TEST - 10 EMAILS FOR SAME COMPANY")
    print("=" * 60)
    
    restaurant = {
        "first_name": "Tony",
        "organization_name": "Luigi's Italian Kitchen",
        "industry": "Food Service",
        "organization_short_description": "Italian restaurant"
    }
    
    emails = []
    for i in range(10):
        email = generate_mass_campaign_email(restaurant, i)
        emails.append(email)
        print(f"\n### EMAIL #{i+1} ###")
        print(email)
    
    # Check uniqueness
    print("\n" + "=" * 60)
    print("UNIQUENESS CHECK:")
    print(f"Total emails: {len(emails)}")
    print(f"Unique emails: {len(set(emails))}")
    print(f"All different: {len(emails) == len(set(emails))}")

if __name__ == "__main__":
    test_mass_variation()