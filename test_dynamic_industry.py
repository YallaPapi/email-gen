import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Try to get API key from environment or use a placeholder
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Please set OPENAI_API_KEY environment variable")
    print("\nShowing mock examples of what would be generated:\n")
    USE_MOCK = True
else:
    client = OpenAI(api_key=api_key)
    USE_MOCK = False

def generate_dynamic_industry_email(row_data):
    """Generate email that dynamically analyzes industry and creates 3 solutions"""
    
    first_name = row_data.get('first_name', 'there')
    company_name = row_data.get('organization_name', 'your company')
    industry = row_data.get('industry', '')
    org_description = row_data.get('organization_short_description', '')
    
    # Dynamic prompt that analyzes the industry on the fly
    system_prompt = f"""You are writing a cold email to someone in the {industry} industry.

TASK: Analyze this industry and identify 3 common problems they face. Then provide 3 AI solutions.

CRITICAL REQUIREMENTS:
1. Think about what specific problems the {industry} industry faces
2. Provide exactly 3 AI-powered solutions that would help
3. ONE of the 3 MUST be either "AI lead generation" or "customer service chatbots" 
4. The other 2 should be highly specific to {industry} problems
5. Don't use generic business language - be specific to their industry

Structure:
- Casual greeting
- Acknowledge their company/role
- Mention you work in AI automation
- List 3 specific AI solutions (bullets or numbered)
- End with: "If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"

Keep it under 100 words. Be conversational and specific to {industry}."""

    user_prompt = f"""Write a cold email to:
Name: {first_name}
Company: {company_name}
Industry: {industry}
Description: {org_description if org_description else 'N/A'}

Remember: Include 3 AI solutions - one must be lead generation or chatbots, the other 2 specific to {industry}."""

    if USE_MOCK:
        # Return mock examples
        if industry.lower() == "healthcare":
            return f"""Hey {first_name},

I noticed {company_name} is in healthcare. Patient scheduling and insurance claims probably eat up a lot of your team's time.

We help healthcare organizations like yours with AI automation:

• Intelligent patient intake that auto-schedules and verifies insurance
• AI-powered medical record search that finds patient history in seconds
• Lead generation for new patient acquisition through targeted outreach

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
        
        elif industry.lower() == "law practice" or industry.lower() == "legal":
            return f"""Hi {first_name},

Running {company_name}, you're probably drowning in document review and billable hour tracking.

Our AI platform helps law firms automate:

• Contract analysis AI that flags key terms and risks instantly
• Automated time tracking that captures billable work without manual entry
• Client lead generation through AI-targeted campaigns

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
        
        elif industry.lower() == "real estate":
            return f"""Hey {first_name},

I work with real estate companies, and I know {company_name} probably deals with endless property inquiries and lead qualification.

We've built AI solutions specifically for real estate:

• Smart property matching that connects buyers to listings automatically
• Virtual showing scheduler with AI follow-ups
• Lead generation chatbots that qualify buyers 24/7

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
        
        elif industry.lower() == "manufacturing":
            return f"""Hi {first_name},

{company_name} being in manufacturing, I imagine production scheduling and quality control are constant challenges.

Our AI helps manufacturers with:

• Predictive maintenance AI that prevents equipment failures
• Quality control automation using computer vision
• B2B lead generation for new contracts and partnerships

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
        
        else:
            return f"""Hey {first_name},

I noticed {company_name} operates in {industry}. Like most {industry} companies, you're probably looking to streamline operations.

We specialize in AI automation for {industry}:

• Process automation tailored to {industry} workflows
• Customer service chatbots trained on {industry} knowledge
• Smart analytics for {industry}-specific metrics

If you're interested in exploring any of these, let's set up a quick call. If not, no worries!"""
    
    else:
        # Use actual OpenAI API
        time.sleep(1)  # Rate limiting
        
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
        
        # Clean up
        lines = [line.strip() for line in email.split('\n') if line.strip()]
        cleaned = '\n\n'.join(lines)
        
        return cleaned

def run_tests():
    """Run test with different industries"""
    
    print("=" * 60)
    print("DYNAMIC INDUSTRY EMAIL GENERATION - NO HARDCODED DICTIONARY")
    print("=" * 60)
    
    # Test 1: 5 different industries
    print("\n### TEST 1: 5 DIFFERENT INDUSTRIES ###\n")
    
    test_data = [
        {
            "first_name": "John",
            "organization_name": "Smith & Associates", 
            "industry": "Law Practice",
            "organization_short_description": "Corporate law firm specializing in M&A"
        },
        {
            "first_name": "Sarah",
            "organization_name": "Regional Medical Center",
            "industry": "Healthcare", 
            "organization_short_description": "350-bed hospital serving the metro area"
        },
        {
            "first_name": "Mike",
            "organization_name": "TechManufacturing Co",
            "industry": "Manufacturing",
            "organization_short_description": "Precision parts for aerospace industry"
        },
        {
            "first_name": "Lisa",
            "organization_name": "Prime Realty Group",
            "industry": "Real Estate",
            "organization_short_description": "Commercial and residential brokerage"
        },
        {
            "first_name": "David",
            "organization_name": "FreshBite Restaurants",
            "industry": "Food Service",
            "organization_short_description": "Chain of fast-casual dining locations"
        }
    ]
    
    for i, data in enumerate(test_data, 1):
        print(f"Email #{i} - {data['industry']}")
        print(f"To: {data['first_name']} at {data['organization_name']}")
        print("-" * 40)
        email = generate_dynamic_industry_email(data)
        print(email)
        print("\n")
    
    # Test 2: Same industry 3 times
    print("\n### TEST 2: SAME INDUSTRY (HEALTHCARE) - 3 VARIATIONS ###\n")
    
    healthcare_data = [
        {
            "first_name": "Emily",
            "organization_name": "Valley Medical",
            "industry": "Healthcare",
            "organization_short_description": "Community hospital and urgent care network"
        },
        {
            "first_name": "Robert", 
            "organization_name": "CareFirst Clinics",
            "industry": "Healthcare",
            "organization_short_description": "Primary care and specialty services"
        },
        {
            "first_name": "Jennifer",
            "organization_name": "Metro Health System",
            "industry": "Healthcare", 
            "organization_short_description": "Integrated healthcare delivery network"
        }
    ]
    
    for i, data in enumerate(healthcare_data, 1):
        print(f"Healthcare Variation #{i}")
        print(f"To: {data['first_name']} at {data['organization_name']}")
        print("-" * 40)
        email = generate_dynamic_industry_email(data)
        print(email)
        print("\n")

if __name__ == "__main__":
    run_tests()