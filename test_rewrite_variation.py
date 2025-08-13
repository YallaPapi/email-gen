import random
import hashlib

def generate_base_email(row_data):
    """Generate a base email with 3 AI solutions"""
    
    first_name = row_data.get('first_name', 'there')
    company_name = row_data.get('organization_name', 'your company')
    industry = row_data.get('industry', '')
    org_description = row_data.get('organization_short_description', '')
    
    # Base template
    base = f"""Hey {first_name},

I noticed {company_name} is in the {industry} industry. Like most {industry} companies, you probably face challenges with operations and customer management.

We offer AI solutions for {industry}:

• AI lead generation for new customers
• Process automation for daily operations
• Customer service chatbots for inquiries

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
    
    return base

def rewrite_email_with_variation(base_email, row_data, iteration):
    """Rewrite the base email with forced variation based on iteration number"""
    
    first_name = row_data.get('first_name', 'there')
    company_name = row_data.get('organization_name', 'your company')
    industry = row_data.get('industry', '')
    org_description = row_data.get('organization_short_description', '')
    
    # Create a hash of the row data to ensure deterministic but different variations
    data_hash = hashlib.md5(f"{company_name}{iteration}".encode()).hexdigest()
    seed = int(data_hash[:8], 16)
    random.seed(seed)
    
    # Different rewrite strategies based on iteration
    rewrite_rules = iteration % 5
    
    if rewrite_rules == 0:
        # Strategy 1: Question opening, numbered list, different CTA
        email = f"""{first_name}, quick question -

Ever feel like {random.choice(['running', 'managing', 'operating'])} {company_name} means constantly {random.choice(['juggling', 'battling', 'fighting'])} {random.choice(['inefficiencies', 'manual tasks', 'repetitive work'])}?

{random.choice(["I've got", "We have", "There are"])} 3 AI tools that could help:

1. {random.choice(['Automated lead capture', 'Smart lead generation', 'AI-powered customer acquisition'])} that {random.choice(['finds', 'identifies', 'targets'])} ideal {industry} customers
2. {random.choice(['Workflow automation', 'Operations AI', 'Process optimization'])} to {random.choice(['eliminate', 'reduce', 'slash'])} manual work
3. {random.choice(['24/7 chat support', 'Intelligent chatbots', 'AI customer service'])} handling {random.choice(['questions', 'inquiries', 'support'])} instantly

{random.choice(['Worth a chat?', 'Want to hear more?', 'Interested?'])} {random.choice(['Happy to explain.', "I'll show you how.", 'Can walk you through it.'])} {random.choice(['No pressure if not.', 'All good either way.', 'No biggie if not.'])}"""
    
    elif rewrite_rules == 1:
        # Strategy 2: Pain point focus, bullets with dashes, casual close
        pain_points = ['staff costs', 'customer retention', 'operational efficiency', 'time management', 'growth challenges']
        selected_pain = random.choice(pain_points)
        
        email = f"""{random.choice(['Hi', 'Hey'])} {first_name} -

{random.choice(['Been thinking about', 'Was looking at', 'Noticed'])} {company_name}. {random.choice(['Bet', 'Guessing', 'Imagine'])} {selected_pain} is {random.choice(['a constant battle', 'always an issue', 'taking up your time'])}.

{random.choice(['Some', 'A few', 'Three'])} AI solutions we {random.choice(['built', 'developed', 'created'])} for {industry}:

- {random.choice(['Lead gen AI', 'Customer acquisition bots', 'Automated prospecting'])} that {random.choice(['works 24/7', 'never stops', 'runs constantly'])}
- {random.choice(['Task automation', 'Smart workflows', 'AI operations'])} {random.choice(['saving hours daily', 'cutting busywork', 'freeing up time'])}
- {random.choice(['Support bots', 'Service AI', 'Chat automation'])} {random.choice(['answering instantly', 'helping customers', 'reducing workload'])}

{random.choice(['If this resonates', 'If any of this helps', 'If this sounds useful'])} - {random.choice(["let's talk", 'quick call?', 'chat soon?'])} {random.choice(['Otherwise', 'If not', 'Or not'])} - {random.choice(['totally fine', 'no stress', 'all good'])}"""
    
    elif rewrite_rules == 2:
        # Strategy 3: Story/example approach, inline solutions, different ending
        email = f"""{first_name},

{random.choice(['Just helped another', 'Recently worked with a', 'Been helping a'])} {industry} {random.choice(['company', 'business', 'organization'])} {random.choice(['automate', 'streamline', 'transform'])} their {random.choice(['operations', 'processes', 'workflows'])}.

{random.choice(['The combo', 'What worked', 'The setup'])}: {random.choice(['automated lead finding', 'AI lead generation', 'smart prospecting'])} + {random.choice(['operational AI', 'workflow automation', 'process optimization'])} + {random.choice(['customer chatbots', 'service automation', 'support AI'])}. {random.choice(['Results were solid.', 'Worked great.', 'Big improvement.'])}

{random.choice(['Could do similar for', 'Same approach would work for', 'Think this could help'])} {company_name}?

{random.choice(['Let me know', 'Your call', 'Up to you'])} - {random.choice(['either way works', "won't bug you if not interested", 'no hard feelings if not'])}."""
    
    elif rewrite_rules == 3:
        # Strategy 4: Direct value prop, specific benefits, short CTA
        email = f"""{first_name} - {random.choice(['real quick', 'quick thought', '30 seconds'])}:

{company_name} could {random.choice(['probably', 'likely', 'potentially'])} {random.choice(['save', 'free up', 'reclaim'])} {random.choice(['10+ hours/week', '40% of admin time', 'tons of time'])} with AI.

{random.choice(['Specifically', 'Talking about', 'I mean'])}:
• {random.choice(['Lead gen running on autopilot', 'Leads coming in automatically', 'AI finding customers for you'])}
• {random.choice(['Repetitive tasks gone', 'Manual work automated', 'Busywork eliminated'])}
• {random.choice(['Customers helped instantly', 'Support handled automatically', 'Questions answered 24/7'])}

{random.choice(['Worth exploring?', 'Make sense?', 'Sound helpful?'])} {random.choice(['Yes = quick call.', 'If yes, we chat.', 'Yeah? = 15 min call.'])} {random.choice(['No = no worries.', "No = I'll leave you be.", 'Nah? = all good.'])}"""
    
    else:
        # Strategy 5: Conversational, natural flow, soft pitch
        email = f"""{random.choice(['Hey', 'Hi'])} {first_name}, {random.choice(['hope things are good', "hope you're well", 'hope all is good'])} at {company_name}.

{random.choice(["I help", "We help", "I work with"])} {industry} {random.choice(['companies', 'businesses', 'organizations'])} {random.choice(['leverage', 'use', 'implement'])} AI - {random.choice(['nothing fancy', 'pretty straightforward', 'simple stuff'])}. {random.choice(['Things like', 'Stuff like', 'Basically'])} {random.choice(['finding leads automatically', 'automated lead generation', 'AI prospecting'])} so {random.choice(["you're not", "you don't have to", "no need for"])} {random.choice(['cold calling', 'manual outreach', 'chasing leads'])}. {random.choice(['Plus', 'Also', 'And'])} {random.choice(['automating', 'handling', 'taking care of'])} the {random.choice(['boring stuff', 'repetitive tasks', 'routine work'])} and {random.choice(['customer questions', 'support tickets', 'inquiries'])} with {random.choice(['smart bots', 'AI', 'automation'])}.

{random.choice(['If that sounds interesting', "If you're curious", 'If any of that resonates'])} - {random.choice(['we could chat', "let's connect", 'happy to discuss'])}. {random.choice(['If not', 'Otherwise', 'Or if not'])} - {random.choice(['genuinely no problem', 'honestly all good', 'totally understand'])}!"""
    
    return email

def test_extreme_variation():
    """Test with same company 5 times to show variation"""
    
    print("=" * 60)
    print("5 EMAILS FOR SAME RESTAURANT - MAXIMUM VARIATION")
    print("=" * 60)
    
    # Same restaurant data
    restaurant = {
        "first_name": "Tony",
        "organization_name": "Luigi's Italian Kitchen",
        "industry": "Food Service",
        "organization_short_description": "family-owned Italian restaurant"
    }
    
    base = generate_base_email(restaurant)
    
    print("\n### BASE EMAIL (before rewriting) ###")
    print("-" * 40)
    print(base)
    print("\n" + "=" * 60)
    print("NOW SHOWING 5 REWRITES WITH FORCED VARIATION:")
    print("=" * 60)
    
    for i in range(5):
        print(f"\n### REWRITE #{i+1} ###")
        print("-" * 40)
        email = rewrite_email_with_variation(base, restaurant, i)
        print(email)
        print()

if __name__ == "__main__":
    test_extreme_variation()