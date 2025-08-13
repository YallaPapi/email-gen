import os
import time
import pandas as pd
from celery import Celery
from openai import OpenAI
from dotenv import load_dotenv
import random

load_dotenv()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    },
    "restaurants": {
        "pain_points": ["reservation management", "staff scheduling", "inventory waste", "customer feedback tracking"],
        "solutions": [
            "Smart reservation system with no-show prediction",
            "Staff scheduling AI based on demand",
            "Inventory optimization to reduce waste",
            "Customer feedback analysis and response automation",
            "AI lead generation for catering clients",
            "Sales automation for event bookings",
            "Customer service chatbots for reservations"
        ]
    }
}

# Default for unknown industries
default_guidance = {
    "pain_points": ["manual processes taking too much time", "difficulty tracking leads and customers", "inconsistent follow-up with prospects", "customer service overload"],
    "solutions": [
        "Process automation that handles repetitive tasks",
        "CRM automation that tracks all interactions",
        "Follow-up automation that never misses a lead",
        "AI lead generation systems",
        "Sales automation workflows",
        "Customer service chatbots",
        "Database reactivation via SMS"
    ]
}

def process_industry_email(row_data, row_index):
    """Generate email with 3 AI solutions tailored to industry"""
    try:
        # Extract key fields
        first_name = row_data.get('first_name', 'there')
        company_name = row_data.get('organization_name', 'your company')
        industry = row_data.get('industry', '').lower().replace(' ', '_').replace('&', 'and')
        org_description = row_data.get('organization_short_description', '')
        
        # Get industry-specific guidance or use default
        guidance = industry_guidance.get(industry, default_guidance)
        
        # Pick 2-3 random pain points
        selected_pain_points = random.sample(guidance["pain_points"], min(3, len(guidance["pain_points"])))
        pain_points_str = ", ".join(selected_pain_points)
        
        # Create the system prompt with 3 solutions approach
        system_prompt = f"""
Write a cold email to this prospect in the {industry.replace('_', ' ')} industry.

Their most common pain points are: {pain_points_str}

Here are AI solutions we offer: {", ".join(guidance["solutions"])}

IMPORTANT: Pick exactly 3 solutions from the list above. Make sure to:
1. Always include either "AI lead generation" or "Customer service chatbots" as one of the 3
2. Pick 2 other solutions that directly address their industry pain points
3. Rephrase each solution in your own words - don't copy verbatim
4. Present them as specific benefits, not generic features

Keep it conversational and under 100 words. End with: "If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"
"""
        
        user_prompt = f"""
Contact: {first_name} at {company_name}
Industry: {industry.replace('_', ' ')}
Description: {org_description if org_description else 'N/A'}

Write a personalized email that shows you understand their industry challenges and offer 3 specific AI solutions.
"""
        
        # Rate limiting
        time.sleep(1)
        
        # Call OpenAI
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=150
        )
        
        email = completion.choices[0].message.content.strip()
        
        # Clean up email
        email = email.replace("Subject:", "").strip()
        lines = email.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not any(sig in line.lower() for sig in ['best regards', 'sincerely', '[your name]']):
                cleaned_lines.append(line)
        
        return '\n\n'.join(cleaned_lines)
        
    except Exception as e:
        return f"ERROR: {str(e)}"

def test_industry_emails():
    """Test function to generate sample emails"""
    
    # Test 1: 5 different industries
    print("=" * 50)
    print("TEST 1: 5 Different Industries")
    print("=" * 50)
    
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
        email = process_industry_email(data, i)
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
        email = process_industry_email(data, i)
        print(email)

if __name__ == "__main__":
    test_industry_emails()