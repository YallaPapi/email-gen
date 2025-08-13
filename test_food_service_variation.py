import random

def generate_food_service_email_mock(row_data, variation_seed):
    """Generate varied emails for food service industry"""
    
    first_name = row_data.get('first_name', 'there')
    company_name = row_data.get('organization_name', 'your restaurant')
    org_description = row_data.get('organization_short_description', '')
    
    # Set seed for this variation to ensure different outputs
    random.seed(variation_seed)
    
    # Pool of food service pain points
    pain_points = [
        "inventory waste and food costs",
        "staff scheduling and labor costs", 
        "table turnover optimization",
        "online ordering and delivery management",
        "customer wait times",
        "reservation no-shows",
        "menu pricing optimization",
        "food safety compliance tracking",
        "customer feedback management",
        "kitchen efficiency"
    ]
    
    # Pool of AI solutions for food service
    ai_solutions = [
        "AI-powered inventory prediction that reduces food waste by 30%",
        "Smart scheduling that matches staff levels to predicted demand",
        "Table management AI that optimizes seating and reduces wait times",
        "Automated online ordering with smart upselling",
        "Customer service chatbots for reservations and orders",
        "AI lead generation for catering and event bookings",
        "Predictive analytics for menu optimization and pricing",
        "Automated food safety monitoring and compliance reporting",
        "Sentiment analysis on reviews with automated responses",
        "Kitchen display systems with AI-optimized order routing",
        "Dynamic pricing based on demand and inventory levels",
        "Voice AI for drive-thru and phone orders",
        "Loyalty program automation with personalized offers",
        "Supply chain optimization to predict shortages"
    ]
    
    # Different opening styles
    openings = [
        f"Hey {first_name},\n\nI noticed {company_name} {org_description}. In food service, {random.choice(pain_points)} can really impact your bottom line.",
        f"Hi {first_name},\n\nRunning {company_name}, you probably deal with {random.choice(pain_points)} daily.",
        f"{first_name},\n\nI work with restaurants like {company_name}, and I know {random.choice(pain_points)} is always a challenge.",
        f"Hey {first_name},\n\nWith {company_name} being {org_description}, I imagine {random.choice(pain_points)} takes up a lot of your time.",
        f"Hi {first_name},\n\nI've helped similar restaurants to {company_name} tackle {random.choice(pain_points)} with AI."
    ]
    
    # Pick a random opening
    opening = random.choice(openings)
    
    # Pick 3 solutions - ensure one is lead gen or chatbot
    lead_gen_chatbot = [s for s in ai_solutions if "lead generation" in s or "chatbot" in s]
    other_solutions = [s for s in ai_solutions if s not in lead_gen_chatbot]
    
    selected = random.sample(lead_gen_chatbot, 1) + random.sample(other_solutions, 2)
    random.shuffle(selected)  # Randomize order
    
    # Different middle sections
    middle_templates = [
        f"\n\nWe help restaurants automate with AI:\n\n• {selected[0]}\n• {selected[1]}\n• {selected[2]}",
        f"\n\nOur AI platform specifically helps restaurants like yours:\n\n• {selected[0]}\n• {selected[1]}\n• {selected[2]}",
        f"\n\nHere's what our AI can do for {company_name}:\n\n• {selected[0]}\n• {selected[1]}\n• {selected[2]}",
        f"\n\nWe've built AI solutions for restaurants:\n\n• {selected[0]}\n• {selected[1]}\n• {selected[2]}",
        f"\n\nThree ways AI could transform your operations:\n\n• {selected[0]}\n• {selected[1]}\n• {selected[2]}"
    ]
    
    middle = random.choice(middle_templates)
    
    # Consistent ending
    ending = "\n\nIf you're interested in exploring any of these, let's set up a quick call. If not, no worries!"
    
    return opening + middle + ending

def test_food_service_variations():
    """Generate 5 different emails for food service restaurants"""
    
    print("=" * 60)
    print("5 FOOD SERVICE EMAILS - TESTING VARIATION")
    print("=" * 60)
    
    restaurants = [
        {
            "first_name": "Tony",
            "organization_name": "Luigi's Italian Kitchen",
            "industry": "Food Service",
            "organization_short_description": "family-owned Italian restaurant with 3 locations"
        },
        {
            "first_name": "Maria",
            "organization_name": "The Burger Joint",
            "industry": "Food Service", 
            "organization_short_description": "fast-casual burger chain"
        },
        {
            "first_name": "James",
            "organization_name": "Sakura Sushi Bar",
            "industry": "Food Service",
            "organization_short_description": "upscale Japanese restaurant and sushi bar"
        },
        {
            "first_name": "Sandra",
            "organization_name": "Café Sunrise",
            "industry": "Food Service",
            "organization_short_description": "breakfast and brunch spot with 2 locations"
        },
        {
            "first_name": "Miguel",
            "organization_name": "Taco Fiesta",
            "industry": "Food Service",
            "organization_short_description": "Mexican street food restaurant"
        }
    ]
    
    for i, data in enumerate(restaurants, 1):
        print(f"\n### EMAIL #{i} ###")
        print(f"To: {data['first_name']} at {data['organization_name']}")
        print("-" * 40)
        # Use different seed for each to ensure variation
        email = generate_food_service_email_mock(data, variation_seed=i*100)
        print(email)
        print()

if __name__ == "__main__":
    test_food_service_variations()