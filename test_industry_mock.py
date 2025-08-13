import random

# Industry guidance dictionary with pain points and solutions
industry_guidance = {
    "law_practice": {
        "pain_points": ["document review bottlenecks", "manual billing processes", "client intake inefficiencies", "case research time consumption"],
        "solutions": [
            "Document automation AI for contracts and legal research",
            "Automated billing and time tracking systems", 
            "Client intake AI that qualifies leads",
            "Case management automation with deadline tracking",
            "AI lead generation for new clients",
            "Sales automation for follow-ups",
            "Customer service chatbots for client questions"
        ]
    },
    "healthcare": {
        "pain_points": ["patient scheduling delays", "medical record management", "staff scheduling conflicts", "insurance processing bottlenecks"],
        "solutions": [
            "Patient scheduling automation with smart reminders",
            "Medical record AI for instant retrieval",
            "Healthcare staff scheduling optimization",
            "Insurance processing automation",
            "AI lead generation for patient acquisition",
            "Sales automation for healthcare services",
            "Customer service chatbots for patient inquiries"
        ]
    },
    "real_estate": {
        "pain_points": ["lead qualification time", "property listing management", "client follow-up gaps", "market analysis delays"],
        "solutions": [
            "Real estate lead qualification AI",
            "Property listing automation with virtual tours",
            "Automated follow-up sequences for buyers",
            "Market analysis AI for pricing optimization",
            "AI lead generation for property buyers",
            "Sales automation for closing deals",
            "Customer service chatbots for property inquiries"
        ]
    },
    "financial_services": {
        "pain_points": ["client onboarding delays", "risk assessment accuracy", "portfolio management complexity", "regulatory compliance tracking"],
        "solutions": [
            "Client onboarding automation with KYC",
            "AI-powered risk assessment models",
            "Portfolio management optimization systems",
            "Compliance tracking and reporting automation",
            "AI lead generation for financial clients",
            "Sales automation for financial products",
            "Customer service chatbots for account inquiries"
        ]
    },
    "manufacturing": {
        "pain_points": ["production line inefficiencies", "inventory management", "quality control issues", "supply chain disruptions"],
        "solutions": [
            "Production line optimization AI",
            "Smart inventory management systems",
            "Quality control automation with computer vision",
            "Supply chain prediction and optimization",
            "AI lead generation for B2B clients",
            "Sales automation for manufacturing orders",
            "Customer service chatbots for order tracking"
        ]
    }
}

def create_mock_email(first_name, company_name, industry, description, variation=1):
    """Create mock email showing the structure of what would be generated"""
    
    guidance = industry_guidance.get(industry, {})
    if not guidance:
        return f"No guidance found for {industry}"
    
    # Randomly select pain points and solutions for variation
    random.seed(variation)  # Use variation as seed for reproducibility but different outputs
    selected_pain_points = random.sample(guidance["pain_points"], min(2, len(guidance["pain_points"])))
    
    # Always include lead gen or chatbot, plus 2 industry-specific
    all_solutions = guidance["solutions"]
    lead_gen_chatbot = [s for s in all_solutions if "lead generation" in s.lower() or "chatbot" in s.lower()]
    industry_specific = [s for s in all_solutions if s not in lead_gen_chatbot]
    
    selected_solutions = random.sample(lead_gen_chatbot, 1) + random.sample(industry_specific, 2)
    
    # Create different variations based on the variation number
    if variation == 1:
        email = f"""Hey {first_name},

I noticed {company_name} is {description}. With {selected_pain_points[0]}, I imagine you're looking for ways to streamline operations.

We specialize in AI solutions for {industry.replace('_', ' ')} companies. Here's what we can help with:

• {selected_solutions[0].replace('AI', 'intelligent').replace('automation', 'automated systems')}
• {selected_solutions[1].replace('automation', 'AI-powered').replace('AI', 'smart')}
• {selected_solutions[2].replace('systems', 'solutions').replace('automation', 'intelligent processing')}

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""

    elif variation == 2:
        email = f"""Hi {first_name},

Running {company_name}, you probably deal with {selected_pain_points[0]} regularly. That's exactly what our AI tools are designed to solve.

We've helped similar {industry.replace('_', ' ')} organizations with:

• {selected_solutions[1].replace('AI', 'machine learning').replace('automation', 'workflow optimization')}
• {selected_solutions[0].replace('automation', 'smart systems').replace('AI', 'automated')}
• {selected_solutions[2].replace('systems', 'platforms').replace('automation', 'AI optimization')}

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""

    else:
        email = f"""Hey {first_name},

I work with {industry.replace('_', ' ')} companies like {company_name}, and I know {selected_pain_points[0]} can be a real challenge.

Our AI platform addresses this with:

• {selected_solutions[2].replace('AI', 'intelligent').replace('systems', 'tools')}
• {selected_solutions[0].replace('automation', 'AI systems').replace('AI', 'smart')}
• {selected_solutions[1].replace('automation', 'automated workflows').replace('systems', 'solutions')}

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
    
    return email

def test_industry_emails():
    """Test function to show sample email structure"""
    
    # Test 1: 5 different industries
    print("=" * 50)
    print("TEST 1: 5 Different Industries")
    print("=" * 50)
    print("\nNOTE: These are mock examples showing the structure.")
    print("With real OpenAI API, the language would be more natural and varied.\n")
    
    test_data_different = [
        {"first_name": "John", "organization_name": "Smith Law Firm", "industry": "law_practice", "organization_short_description": "Corporate law firm specializing in mergers and acquisitions"},
        {"first_name": "Sarah", "organization_name": "City Medical Center", "industry": "healthcare", "organization_short_description": "Multi-specialty medical center with 200+ beds"},
        {"first_name": "Mike", "organization_name": "Prime Properties", "industry": "real_estate", "organization_short_description": "Commercial real estate brokerage"},
        {"first_name": "Lisa", "organization_name": "Capital Advisors", "industry": "financial_services", "organization_short_description": "Wealth management and investment advisory"},
        {"first_name": "Tom", "organization_name": "TechParts Manufacturing", "industry": "manufacturing", "organization_short_description": "Precision parts manufacturer for aerospace"}
    ]
    
    for i, data in enumerate(test_data_different):
        print(f"\n--- Email {i+1}: {data['industry']} ---")
        print(f"To: {data['first_name']} at {data['organization_name']}")
        print("-" * 30)
        email = create_mock_email(
            data['first_name'], 
            data['organization_name'], 
            data['industry'], 
            data['organization_short_description'],
            variation=1
        )
        print(email)
    
    # Test 2: Same industry 3 times
    print("\n" + "=" * 50)
    print("TEST 2: Same Industry (Healthcare) - 3 Variations")
    print("=" * 50)
    
    test_data_same = [
        {"first_name": "Emily", "organization_name": "Regional Hospital", "industry": "healthcare", "organization_short_description": "Regional hospital serving 5 counties"},
        {"first_name": "David", "organization_name": "MedClinic Plus", "industry": "healthcare", "organization_short_description": "Network of urgent care clinics"},
        {"first_name": "Jennifer", "organization_name": "Wellness Medical Group", "industry": "healthcare", "organization_short_description": "Primary care and specialty services"}
    ]
    
    for i, data in enumerate(test_data_same):
        print(f"\n--- Healthcare Email Variation {i+1} ---")
        print(f"To: {data['first_name']} at {data['organization_name']}")
        print("-" * 30)
        email = create_mock_email(
            data['first_name'], 
            data['organization_name'], 
            data['industry'], 
            data['organization_short_description'],
            variation=i+1  # Different variation for each
        )
        print(email)

if __name__ == "__main__":
    test_industry_emails()