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
    """ULTIMATE NUCLEAR CLEANING - BULLETPROOF CONTENT REMOVAL"""
    import re
    
    text = str(email_text).strip()
    
    # STEP 1: ELIMINATE ALL HIGH UNICODE (EMOJIS) - NUCLEAR APPROACH
    # Remove ALL characters that could be emojis using comprehensive ranges
    import unicodedata
    # Keep only basic printable ASCII, space, newline, tab, carriage return
    allowed_chars = set(range(32, 127))  # printable ASCII
    allowed_chars.update([9, 10, 13])    # tab, newline, carriage return
    
    text = ''.join(char for char in text if ord(char) in allowed_chars)
    
    # STEP 2: BRUTAL PHRASE ELIMINATION - Case insensitive
    death_phrases = [
        'Take care!', 'Take care,', 'Take care', 'take care!', 'take care,', 'take care', 'TAKE CARE',
        'Let me know if you have any questions', 'Let me know if you', 'let me know if you have any questions', 
        'let me know if you', 'let me know if', 'LET ME KNOW IF',
        'Feel free to reach out', 'Feel free to contact', 'feel free to reach out', 'feel free to contact',
        'feel free to', 'FEEL FREE TO',
        'Have a great day', 'Have a wonderful day', 'have a great day', 'have a wonderful day',
        'Looking forward to hearing from you', 'looking forward to hearing from you',
        'Best,', 'best,', 'BEST,', 'Cheers,', 'cheers,', 'CHEERS,',
        'Thanks,', 'thanks,', 'THANKS,', 'Regards,', 'regards,', 'REGARDS,',
        'Best regards', 'best regards', 'BEST REGARDS', 'Best regards.', 'best regards.', 'BEST REGARDS.',
        'Best regards,', 'best regards,', 'BEST REGARDS,', 'Sincerely,', 'sincerely,', 'SINCERELY,',
        'Sincerely', 'sincerely', 'SINCERELY', '[Your Name]', '[your name]', '[YOUR NAME]'
    ]
    
    for phrase in death_phrases:
        text = text.replace(phrase, '')
    
    # STEP 3: Find greeting and remove everything before
    lines = text.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if re.match(r'^\s*(Hey|Hi|Hello)\s+', line.strip(), re.IGNORECASE):
            start_idx = i
            break
    lines = lines[start_idx:]
    
    # STEP 4: LINE-BY-LINE DESTRUCTION
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        
        # KILL signature lines entirely
        signature_kill_patterns = [
            r'^(Take care|Best|Cheers|Thanks|Regards|Sincerely)[,!\s]*$',
            r'^[A-Z][a-z]+\s*$',  # Kill single names like "John", "Alex"
            r'AI Automation',
            r'^(Best|Cheers|Thanks|Regards)$'
        ]
        
        should_kill = False
        for pattern in signature_kill_patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                should_kill = True
                break
        
        if should_kill:
            continue  # KILL this line entirely
            
        # Additional phrase removal from line content
        for phrase in death_phrases:
            line = line.replace(phrase, '')
        
        # Only keep lines with actual content
        if line.strip():
            clean_lines.append(line)
    
    # STEP 5: FINAL ASSEMBLY AND CLEANUP
    result = '\n'.join(clean_lines)
    result = re.sub(r'\n\s*\n+', '\n\n', result)  # Clean up spacing
    
    # STEP 6: FINAL DEATH PASS - Kill anything that survived
    for phrase in death_phrases:
        result = result.replace(phrase, '')
    
    # Remove any remaining high Unicode
    result = ''.join(char for char in result if ord(char) < 256)
    
    return result.strip()

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
        industry = industry_raw if pd.notna(industry_raw) and str(industry_raw).strip() not in ['', 'nan', 'none', 'null'] else 'your industry'
        
        model = model_assigner.get_worker_model()
        
        # STEP 1: Generate initial email - USER'S EXACT PROMPT
        # Check if we have rich data or need template
        org_desc = cleaned_data.get('organization_short_description', '')
        
        # Create industry guidance dictionary for all 140 industries
        industry_guidance = {
            "accounting": {
                "pain_points": ["manual data entry and bookkeeping", "tax compliance tracking", "client invoice management", "financial reporting delays"],
                "solutions": ["Automated bookkeeping that categorizes expenses", "Tax compliance AI that tracks deadlines", "Invoice processing automation", "Financial reporting AI", "AI lead generation for new clients", "Sales automation for service upselling", "Customer service chatbots for client questions"]
            },
            "airlines/aviation": {
                "pain_points": ["flight scheduling optimization", "maintenance tracking", "passenger service delays", "fuel cost management"],
                "solutions": ["Flight scheduling AI that optimizes routes", "Predictive maintenance systems", "Passenger service automation", "Fuel optimization algorithms", "AI lead generation for corporate travel", "Sales automation for booking follow-ups", "Customer service chatbots for flight inquiries"]
            },
            "alternative_dispute_resolution": {
                "pain_points": ["case scheduling conflicts", "document review time", "client communication gaps", "settlement tracking"],
                "solutions": ["Case scheduling automation", "Document analysis AI for faster review", "Client communication automation", "Settlement tracking systems", "AI lead generation for legal clients", "Sales automation for case follow-ups", "Customer service chatbots for case updates"]
            },
            "alternative_medicine": {
                "pain_points": ["patient appointment scheduling", "treatment plan tracking", "insurance claim processing", "patient follow-up management"],
                "solutions": ["Appointment scheduling automation", "Treatment tracking AI systems", "Insurance claim processing automation", "Patient follow-up automation", "AI lead generation for new patients", "Sales automation for treatment packages", "Customer service chatbots for patient inquiries"]
            },
            "animation": {
                "pain_points": ["project timeline management", "client revision tracking", "asset organization", "team collaboration issues"],
                "solutions": ["Project management AI for animation timelines", "Revision tracking automation", "Asset management systems with AI tagging", "Team collaboration tools", "AI lead generation for animation projects", "Sales automation for client follow-ups", "Customer service chatbots for project updates"]
            },
            "apparel_and_fashion": {
                "pain_points": ["inventory management", "trend forecasting", "supply chain delays", "customer size recommendations"],
                "solutions": ["AI inventory management that predicts fashion trends", "Trend forecasting algorithms", "Supply chain optimization", "Size recommendation AI", "AI lead generation for fashion brands", "Sales automation for seasonal campaigns", "Customer service chatbots for sizing help"]
            },
            "architecture_and_planning": {
                "pain_points": ["project design revisions", "permit tracking", "client approval delays", "construction timeline coordination"],
                "solutions": ["Design revision automation", "Permit tracking AI systems", "Client approval workflow automation", "Construction timeline optimization", "AI lead generation for architectural projects", "Sales automation for project follow-ups", "Customer service chatbots for project status"]
            },
            "arts_and_crafts": {
                "pain_points": ["inventory tracking for supplies", "custom order management", "pricing calculations", "seasonal demand planning"],
                "solutions": ["Supply inventory AI management", "Custom order tracking automation", "Dynamic pricing algorithms", "Demand forecasting for seasonal items", "AI lead generation for craft customers", "Sales automation for repeat buyers", "Customer service chatbots for custom orders"]
            },
            "automotive": {
                "pain_points": ["inventory management for parts", "service scheduling", "warranty tracking", "customer service delays"],
                "solutions": ["Parts inventory AI optimization", "Service scheduling automation", "Warranty tracking systems", "Customer service automation", "AI lead generation for automotive services", "Sales automation for service packages", "Customer service chatbots for appointment booking"]
            },
            "aviation_and_aerospace": {
                "pain_points": ["maintenance scheduling", "compliance tracking", "supply chain management", "safety documentation"],
                "solutions": ["Predictive maintenance AI systems", "Compliance tracking automation", "Supply chain optimization", "Safety documentation automation", "AI lead generation for aerospace contracts", "Sales automation for B2B follow-ups", "Customer service chatbots for technical inquiries"]
            },
            "banking": {
                "pain_points": ["loan processing delays", "fraud detection", "customer service wait times", "regulatory compliance"],
                "solutions": ["Loan processing automation", "AI fraud detection systems", "Customer service chatbots for banking", "Compliance tracking automation", "AI lead generation for banking services", "Sales automation for financial products", "Customer service chatbots for account inquiries"]
            },
            "biotechnology": {
                "pain_points": ["research data management", "regulatory compliance", "clinical trial tracking", "patent research"],
                "solutions": ["Research data AI analysis", "Regulatory compliance automation", "Clinical trial management systems", "Patent research automation", "AI lead generation for biotech partnerships", "Sales automation for research collaborations", "Customer service chatbots for technical support"]
            },
            "broadcast_media": {
                "pain_points": ["content scheduling", "audience engagement tracking", "ad placement optimization", "content creation workflows"],
                "solutions": ["Content scheduling automation", "Audience analytics AI", "Ad placement optimization algorithms", "Content workflow automation", "AI lead generation for media advertising", "Sales automation for ad packages", "Customer service chatbots for viewer inquiries"]
            },
            "building_materials": {
                "pain_points": ["inventory management", "supply chain delays", "price fluctuation tracking", "contractor relationship management"],
                "solutions": ["Inventory AI optimization", "Supply chain tracking automation", "Price monitoring systems", "Contractor CRM automation", "AI lead generation for construction projects", "Sales automation for bulk orders", "Customer service chatbots for product inquiries"]
            },
            "business_supplies_and_equipment": {
                "pain_points": ["inventory tracking", "bulk order management", "client reorder scheduling", "equipment maintenance tracking"],
                "solutions": ["Inventory management AI", "Bulk order processing automation", "Reorder scheduling systems", "Equipment maintenance tracking", "AI lead generation for business clients", "Sales automation for repeat orders", "Customer service chatbots for product support"]
            },
            "capital_markets": {
                "pain_points": ["market analysis delays", "risk assessment", "client portfolio management", "regulatory reporting"],
                "solutions": ["AI market analysis systems", "Risk assessment automation", "Portfolio management AI", "Regulatory reporting automation", "AI lead generation for investment clients", "Sales automation for financial services", "Customer service chatbots for market inquiries"]
            },
            "chemicals": {
                "pain_points": ["safety compliance tracking", "inventory management", "quality control testing", "supply chain optimization"],
                "solutions": ["Safety compliance automation", "Chemical inventory AI management", "Quality control automation", "Supply chain optimization", "AI lead generation for chemical buyers", "Sales automation for bulk orders", "Customer service chatbots for technical support"]
            },
            "civic_and_social_organization": {
                "pain_points": ["volunteer coordination", "donation tracking", "event planning", "community engagement"],
                "solutions": ["Volunteer scheduling automation", "Donation tracking AI", "Event planning automation", "Community engagement analytics", "AI lead generation for volunteers", "Sales automation for fundraising", "Customer service chatbots for community questions"]
            },
            "civil_engineering": {
                "pain_points": ["project planning delays", "permit tracking", "safety compliance", "resource allocation"],
                "solutions": ["Project planning AI optimization", "Permit tracking automation", "Safety compliance monitoring", "Resource allocation algorithms", "AI lead generation for engineering projects", "Sales automation for project proposals", "Customer service chatbots for project updates"]
            },
            "commercial_real_estate": {
                "pain_points": ["property listing management", "tenant screening", "lease tracking", "market analysis"],
                "solutions": ["Property listing automation", "Tenant screening AI", "Lease management systems", "Market analysis automation", "AI lead generation for property leads", "Sales automation for lease follow-ups", "Customer service chatbots for property inquiries"]
            },
            "computer_and_network_security": {
                "pain_points": ["threat detection delays", "incident response time", "compliance reporting", "security audit tracking"],
                "solutions": ["AI threat detection systems", "Automated incident response", "Compliance reporting automation", "Security audit tracking", "AI lead generation for security clients", "Sales automation for security services", "Customer service chatbots for security alerts"]
            },
            "computer_games": {
                "pain_points": ["player behavior analysis", "game testing automation", "community management", "monetization optimization"],
                "solutions": ["Player analytics AI", "Automated game testing", "Community management automation", "Monetization optimization algorithms", "AI lead generation for gaming partnerships", "Sales automation for in-game purchases", "Customer service chatbots for player support"]
            },
            "computer_hardware": {
                "pain_points": ["inventory management", "quality control testing", "supply chain delays", "technical support volume"],
                "solutions": ["Hardware inventory AI", "Quality control automation", "Supply chain optimization", "Technical support automation", "AI lead generation for hardware sales", "Sales automation for enterprise clients", "Customer service chatbots for technical support"]
            },
            "computer_networking": {
                "pain_points": ["network monitoring", "troubleshooting delays", "capacity planning", "security management"],
                "solutions": ["Network monitoring AI", "Automated troubleshooting systems", "Capacity planning algorithms", "Security management automation", "AI lead generation for networking clients", "Sales automation for network upgrades", "Customer service chatbots for network issues"]
            },
            "construction": {
                "pain_points": ["project delays and cost overruns", "safety compliance tracking", "crew scheduling conflicts", "material waste and inventory"],
                "solutions": ["Project management AI that tracks progress and predicts delays", "Safety compliance automation and reporting", "Crew scheduling optimization based on project needs", "Material management AI that reduces waste", "AI lead generation for new projects", "Sales automation for client follow-ups", "Customer service chatbots for project updates"]
            },
            "consumer_electronics": {
                "pain_points": ["inventory management", "product lifecycle tracking", "customer support volume", "return processing"],
                "solutions": ["Electronics inventory AI", "Product lifecycle management", "Customer support automation", "Return processing automation", "AI lead generation for electronics sales", "Sales automation for product launches", "Customer service chatbots for product support"]
            },
            "consumer_goods": {
                "pain_points": ["demand forecasting", "inventory optimization", "supply chain management", "customer feedback analysis"],
                "solutions": ["Demand forecasting AI", "Inventory optimization algorithms", "Supply chain automation", "Customer feedback analysis", "AI lead generation for retail partners", "Sales automation for consumer campaigns", "Customer service chatbots for product inquiries"]
            },
            "consumer_services": {
                "pain_points": ["appointment scheduling", "customer service delays", "service quality tracking", "billing automation"],
                "solutions": ["Appointment scheduling automation", "Customer service AI", "Service quality monitoring", "Billing automation systems", "AI lead generation for service clients", "Sales automation for service packages", "Customer service chatbots for service inquiries"]
            },
            "cosmetics": {
                "pain_points": ["inventory management", "trend forecasting", "customer skin analysis", "product recommendation"],
                "solutions": ["Cosmetics inventory AI", "Beauty trend forecasting", "Skin analysis AI", "Product recommendation systems", "AI lead generation for beauty customers", "Sales automation for cosmetic campaigns", "Customer service chatbots for beauty advice"]
            },
            "dairy": {
                "pain_points": ["milk production tracking", "quality control testing", "supply chain management", "inventory freshness"],
                "solutions": ["Production tracking AI", "Quality control automation", "Supply chain optimization", "Freshness monitoring systems", "AI lead generation for dairy distributors", "Sales automation for bulk orders", "Customer service chatbots for product freshness"]
            },
            "defense_and_space": {
                "pain_points": ["project security compliance", "resource allocation", "maintenance scheduling", "mission planning"],
                "solutions": ["Security compliance automation", "Resource allocation AI", "Predictive maintenance systems", "Mission planning optimization", "AI lead generation for defense contracts", "Sales automation for government proposals", "Customer service chatbots for technical specifications"]
            },
            "design": {
                "pain_points": ["project timeline management", "client revision tracking", "asset organization", "team collaboration"],
                "solutions": ["Design project management AI", "Revision tracking automation", "Asset management with AI tagging", "Collaboration workflow automation", "AI lead generation for design clients", "Sales automation for design services", "Customer service chatbots for project status"]
            },
            "e-learning": {
                "pain_points": ["student engagement tracking", "content personalization", "assessment automation", "progress monitoring"],
                "solutions": ["Student engagement analytics", "AI content personalization", "Automated assessment systems", "Progress tracking AI", "AI lead generation for educational institutions", "Sales automation for course enrollment", "Customer service chatbots for student support"]
            },
            "education_management": {
                "pain_points": ["student enrollment tracking", "staff scheduling", "curriculum planning", "performance analytics"],
                "solutions": ["Enrollment management AI", "Staff scheduling automation", "Curriculum planning systems", "Performance analytics AI", "AI lead generation for educational services", "Sales automation for program enrollment", "Customer service chatbots for student inquiries"]
            },
            "electrical/electronic_manufacturing": {
                "pain_points": ["quality control testing", "production line optimization", "inventory management", "defect detection"],
                "solutions": ["Quality control automation", "Production optimization AI", "Manufacturing inventory management", "AI defect detection systems", "AI lead generation for manufacturing clients", "Sales automation for bulk orders", "Customer service chatbots for technical specifications"]
            },
            "entertainment": {
                "pain_points": ["content scheduling", "audience engagement", "talent management", "revenue optimization"],
                "solutions": ["Content scheduling automation", "Audience analytics AI", "Talent management systems", "Revenue optimization algorithms", "AI lead generation for entertainment partnerships", "Sales automation for content licensing", "Customer service chatbots for audience inquiries"]
            },
            "environmental_services": {
                "pain_points": ["compliance tracking", "waste management optimization", "environmental monitoring", "reporting automation"],
                "solutions": ["Environmental compliance AI", "Waste optimization algorithms", "Environmental monitoring automation", "Reporting systems automation", "AI lead generation for environmental clients", "Sales automation for compliance services", "Customer service chatbots for environmental inquiries"]
            },
            "events_services": {
                "pain_points": ["event planning coordination", "vendor management", "attendee tracking", "budget management"],
                "solutions": ["Event planning automation", "Vendor management AI", "Attendee tracking systems", "Budget optimization algorithms", "AI lead generation for event clients", "Sales automation for event packages", "Customer service chatbots for event inquiries"]
            },
            "executive_office": {
                "pain_points": ["meeting scheduling", "document management", "communication coordination", "decision support"],
                "solutions": ["Meeting scheduling automation", "Document management AI", "Communication workflow automation", "Decision support systems", "AI lead generation for executive services", "Sales automation for business services", "Customer service chatbots for administrative support"]
            },
            "facilities_services": {
                "pain_points": ["maintenance scheduling", "space utilization", "vendor coordination", "cost optimization"],
                "solutions": ["Maintenance scheduling AI", "Space utilization analytics", "Vendor coordination automation", "Cost optimization algorithms", "AI lead generation for facilities clients", "Sales automation for service contracts", "Customer service chatbots for facility requests"]
            },
            "manufacturing": {
                "pain_points": ["production line inefficiencies", "quality control issues", "supply chain disruptions", "equipment downtime"],
                "solutions": ["AI chatbots for technical support and order inquiries", "Lead generation systems for finding new manufacturing clients", "Sales automation for quoting and order management", "SMS appointment booking for equipment maintenance and consultations"]
            },
            "technology": {
                "pain_points": ["system scalability issues", "data security concerns", "software integration challenges", "technical debt management"],
                "solutions": ["AI chatbots for customer support and tech inquiries", "Lead generation systems for finding enterprise clients", "Sales automation for software demos and trials", "SMS database reactivation for re-engaging past clients"]
            },
            "farming": {
                "pain_points": ["crop yield optimization", "weather monitoring", "equipment maintenance", "market price tracking"],
                "solutions": ["Crop optimization AI", "Weather prediction systems", "Equipment maintenance automation", "Market price monitoring", "AI lead generation for agricultural buyers", "Sales automation for crop sales", "Customer service chatbots for farming inquiries"]
            },
            "financial_services": {
                "pain_points": ["client onboarding delays", "risk assessment", "portfolio management", "regulatory compliance"],
                "solutions": ["AI chatbots for client inquiries and account support", "Lead generation systems for finding high-value prospects", "Sales automation for appointment scheduling and follow-ups", "SMS database reactivation for re-engaging dormant clients"]
            },
            "fine_art": {
                "pain_points": ["artwork cataloging", "auction management", "authentication verification", "client relationship management"],
                "solutions": ["Artwork cataloging AI", "Auction management automation", "Authentication AI systems", "Art client CRM", "AI lead generation for art collectors", "Sales automation for art sales", "Customer service chatbots for art inquiries"]
            },
            "fishery": {
                "pain_points": ["catch tracking", "quality control", "supply chain management", "regulatory compliance"],
                "solutions": ["Catch tracking automation", "Quality control AI", "Supply chain optimization", "Compliance monitoring systems", "AI lead generation for seafood buyers", "Sales automation for fish sales", "Customer service chatbots for freshness inquiries"]
            },
            "food_and_beverages": {
                "pain_points": ["inventory management", "quality control", "supply chain delays", "customer preference tracking"],
                "solutions": ["Food inventory AI", "Quality control automation", "Supply chain optimization", "Customer preference analytics", "AI lead generation for food distributors", "Sales automation for food products", "Customer service chatbots for product information"]
            },
            "food_production": {
                "pain_points": ["production line optimization", "quality control testing", "inventory management", "safety compliance"],
                "solutions": ["Production optimization AI", "Quality control automation", "Production inventory management", "Safety compliance monitoring", "AI lead generation for food buyers", "Sales automation for bulk food orders", "Customer service chatbots for production inquiries"]
            },
            "fund-raising": {
                "pain_points": ["donor tracking", "campaign management", "event coordination", "impact measurement"],
                "solutions": ["Donor management AI", "Campaign automation systems", "Event planning automation", "Impact analytics", "AI lead generation for donors", "Sales automation for fundraising campaigns", "Customer service chatbots for donor inquiries"]
            },
            "furniture": {
                "pain_points": ["inventory management", "custom order tracking", "delivery scheduling", "customer design preferences"],
                "solutions": ["Furniture inventory AI", "Custom order management", "Delivery optimization", "Design preference analytics", "AI lead generation for furniture customers", "Sales automation for furniture sales", "Customer service chatbots for design consultations"]
            },
            "gambling_and_casinos": {
                "pain_points": ["player behavior analysis", "security monitoring", "revenue optimization", "customer service management"],
                "solutions": ["Player analytics AI", "Security monitoring automation", "Revenue optimization algorithms", "Customer service automation", "AI lead generation for casino marketing", "Sales automation for player retention", "Customer service chatbots for player support"]
            },
            "glass_ceramics_and_concrete": {
                "pain_points": ["quality control testing", "production optimization", "inventory management", "order fulfillment"],
                "solutions": ["Quality control automation", "Production optimization AI", "Materials inventory management", "Order fulfillment automation", "AI lead generation for construction clients", "Sales automation for bulk orders", "Customer service chatbots for material specifications"]
            },
            "government_administration": {
                "pain_points": ["citizen service delays", "document processing", "compliance tracking", "resource allocation"],
                "solutions": ["Citizen service automation", "Document processing AI", "Compliance monitoring systems", "Resource allocation optimization", "AI lead generation for government services", "Sales automation for civic engagement", "Customer service chatbots for citizen inquiries"]
            },
            "government_relations": {
                "pain_points": ["policy tracking", "stakeholder communication", "compliance monitoring", "reporting automation"],
                "solutions": ["Policy tracking AI", "Stakeholder communication automation", "Compliance monitoring systems", "Government reporting automation", "AI lead generation for policy clients", "Sales automation for government services", "Customer service chatbots for policy inquiries"]
            },
            "graphic_design": {
                "pain_points": ["project timeline management", "client revision tracking", "asset organization", "creative workflow"],
                "solutions": ["Design project management", "Revision tracking automation", "Asset management AI", "Creative workflow optimization", "AI lead generation for design clients", "Sales automation for design services", "Customer service chatbots for project updates"]
            },
            "health_wellness_and_fitness": {
                "pain_points": ["member engagement tracking", "class scheduling", "equipment maintenance", "progress monitoring"],
                "solutions": ["Member engagement analytics", "Class scheduling automation", "Equipment maintenance tracking", "Fitness progress AI", "AI lead generation for fitness members", "Sales automation for membership sales", "Customer service chatbots for fitness questions"]
            },
            "healthcare": {
                "pain_points": ["patient scheduling", "medical record management", "staff scheduling", "insurance processing"],
                "solutions": ["AI chatbots for patient inquiries and appointment booking", "Lead generation systems for finding new patients", "Sales automation for patient follow-ups and care coordination", "SMS appointment reminders and database reactivation for lapsed patients"]
            },
            "higher_education": {
                "pain_points": ["student enrollment management", "course scheduling", "academic performance tracking", "research coordination"],
                "solutions": ["Enrollment management AI", "Course scheduling automation", "Academic analytics", "Research coordination systems", "AI lead generation for student recruitment", "Sales automation for program enrollment", "Customer service chatbots for student services"]
            },
            "hospital_and_health_care": {
                "pain_points": ["patient scheduling", "medical record management", "staff scheduling", "insurance processing"],
                "solutions": ["Patient scheduling automation", "Medical record AI", "Healthcare staff scheduling", "Insurance processing automation", "AI lead generation for patient acquisition", "Sales automation for healthcare services", "Customer service chatbots for patient inquiries"]
            },
            "hospitality": {
                "pain_points": ["reservation management", "guest service coordination", "housekeeping scheduling", "revenue optimization"],
                "solutions": ["Reservation management AI", "Guest service automation", "Housekeeping scheduling optimization", "Revenue management systems", "AI lead generation for hotel bookings", "Sales automation for guest services", "Customer service chatbots for hotel inquiries"]
            },
            "human_resources": {
                "pain_points": ["recruitment screening", "employee onboarding", "performance tracking", "benefits administration"],
                "solutions": ["AI recruitment screening", "Onboarding automation", "Performance analytics", "Benefits administration automation", "AI lead generation for HR services", "Sales automation for HR solutions", "Customer service chatbots for employee questions"]
            },
            "import_and_export": {
                "pain_points": ["customs documentation", "shipment tracking", "compliance management", "inventory coordination"],
                "solutions": ["Customs documentation automation", "Shipment tracking AI", "Trade compliance systems", "Import/export inventory management", "AI lead generation for trade partners", "Sales automation for import/export services", "Customer service chatbots for shipment inquiries"]
            },
            "individual_and_family_services": {
                "pain_points": ["client case management", "service coordination", "appointment scheduling", "outcome tracking"],
                "solutions": ["Case management AI", "Service coordination automation", "Appointment scheduling systems", "Outcome tracking analytics", "AI lead generation for family services", "Sales automation for service programs", "Customer service chatbots for family support"]
            },
            "industrial_automation": {
                "pain_points": ["production line optimization", "equipment monitoring", "quality control", "maintenance scheduling"],
                "solutions": ["Production optimization AI", "Equipment monitoring automation", "Quality control systems", "Predictive maintenance", "AI lead generation for industrial clients", "Sales automation for automation solutions", "Customer service chatbots for technical support"]
            },
            "information_services": {
                "pain_points": ["data processing delays", "information accuracy", "client request management", "research automation"],
                "solutions": ["Data processing automation", "Information accuracy AI", "Request management systems", "Research automation tools", "AI lead generation for information clients", "Sales automation for data services", "Customer service chatbots for information requests"]
            },
            "information_technology_and_services": {
                "pain_points": ["system maintenance", "security monitoring", "client support tickets", "project management"],
                "solutions": ["System maintenance automation", "Security monitoring AI", "Support ticket automation", "IT project management", "AI lead generation for IT clients", "Sales automation for IT services", "Customer service chatbots for technical support"]
            },
            "insurance": {
                "pain_points": ["claims processing delays", "risk assessment", "policy management", "fraud detection"],
                "solutions": ["Claims processing automation", "AI risk assessment", "Policy management systems", "Fraud detection AI", "AI lead generation for insurance clients", "Sales automation for policy sales", "Customer service chatbots for policy inquiries"]
            },
            "international_affairs": {
                "pain_points": ["diplomatic communication", "treaty tracking", "cultural coordination", "international compliance"],
                "solutions": ["Diplomatic communication automation", "Treaty tracking systems", "Cultural coordination AI", "International compliance monitoring", "AI lead generation for international partnerships", "Sales automation for diplomatic services", "Customer service chatbots for international inquiries"]
            },
            "international_trade_and_development": {
                "pain_points": ["trade compliance", "development project tracking", "partner coordination", "impact measurement"],
                "solutions": ["Trade compliance automation", "Project tracking systems", "Partner coordination AI", "Development impact analytics", "AI lead generation for trade partners", "Sales automation for development projects", "Customer service chatbots for trade inquiries"]
            },
            "internet": {
                "pain_points": ["website performance optimization", "user engagement tracking", "content management", "security monitoring"],
                "solutions": ["Website optimization AI", "User analytics systems", "Content management automation", "Web security monitoring", "AI lead generation for web services", "Sales automation for internet solutions", "Customer service chatbots for web support"]
            },
            "investment_banking": {
                "pain_points": ["deal pipeline management", "risk analysis", "client relationship tracking", "regulatory compliance"],
                "solutions": ["Deal pipeline AI", "Risk analysis automation", "Client relationship management", "Investment compliance tracking", "AI lead generation for investment clients", "Sales automation for banking services", "Customer service chatbots for investment inquiries"]
            },
            "investment_management": {
                "pain_points": ["portfolio optimization", "risk assessment", "client reporting", "market analysis"],
                "solutions": ["Portfolio optimization AI", "Risk assessment automation", "Client reporting systems", "Market analysis AI", "AI lead generation for investment clients", "Sales automation for portfolio services", "Customer service chatbots for investment questions"]
            },
            "law_enforcement": {
                "pain_points": ["case management", "evidence tracking", "resource allocation", "community engagement"],
                "solutions": ["Case management AI", "Evidence tracking automation", "Resource allocation optimization", "Community engagement systems", "AI lead generation for law enforcement technology", "Sales automation for security services", "Customer service chatbots for public safety inquiries"]
            },
            "law_practice": {
                "pain_points": ["document review bottlenecks", "manual billing processes", "client intake inefficiencies", "case research time consumption"],
                "solutions": ["Document automation AI for contracts and legal research", "Automated billing and time tracking systems", "Client intake AI that qualifies leads", "Case management automation with deadline tracking", "AI lead generation for new clients", "Sales automation for follow-ups", "Customer service chatbots for client questions"]
            },
            "legal_services": {
                "pain_points": ["document preparation", "client consultation scheduling", "billing automation", "case tracking"],
                "solutions": ["Document preparation automation", "Consultation scheduling AI", "Legal billing automation", "Case tracking systems", "AI lead generation for legal clients", "Sales automation for legal services", "Customer service chatbots for legal inquiries"]
            },
            "legislative_office": {
                "pain_points": ["constituent communication", "policy research", "meeting scheduling", "voting tracking"],
                "solutions": ["Constituent communication automation", "Policy research AI", "Legislative scheduling systems", "Voting tracking automation", "AI lead generation for political engagement", "Sales automation for political campaigns", "Customer service chatbots for constituent services"]
            },
            "leisure_travel_and_tourism": {
                "pain_points": ["booking management", "customer experience tracking", "itinerary planning", "seasonal demand forecasting"],
                "solutions": ["Booking management automation", "Customer experience analytics", "AI itinerary planning", "Tourism demand forecasting", "AI lead generation for travel bookings", "Sales automation for travel packages", "Customer service chatbots for travel inquiries"]
            },
            "logistics_and_supply_chain": {
                "pain_points": ["shipment tracking", "route optimization", "inventory coordination", "delivery scheduling"],
                "solutions": ["Shipment tracking automation", "Route optimization AI", "Supply chain inventory management", "Delivery scheduling optimization", "AI lead generation for logistics clients", "Sales automation for shipping services", "Customer service chatbots for shipment tracking"]
            },
            "luxury_goods_and_jewelry": {
                "pain_points": ["inventory management", "authentication verification", "customer personalization", "security tracking"],
                "solutions": ["Luxury inventory AI", "Authentication AI systems", "Customer personalization", "Security tracking automation", "AI lead generation for luxury customers", "Sales automation for high-end sales", "Customer service chatbots for luxury inquiries"]
            },
            "machinery": {
                "pain_points": ["equipment maintenance", "parts inventory", "performance monitoring", "safety compliance"],
                "solutions": ["Predictive maintenance AI", "Parts inventory optimization", "Performance monitoring automation", "Safety compliance tracking", "AI lead generation for machinery clients", "Sales automation for equipment sales", "Customer service chatbots for machinery support"]
            },
            "management_consulting": {
                "pain_points": ["project timeline management", "client engagement tracking", "knowledge management", "proposal development"],
                "solutions": ["Consulting project management", "Client engagement analytics", "Knowledge management AI", "Proposal automation systems", "AI lead generation for consulting clients", "Sales automation for consulting services", "Customer service chatbots for project inquiries"]
            },
            "maritime": {
                "pain_points": ["vessel tracking", "cargo management", "route optimization", "safety compliance"],
                "solutions": ["Vessel tracking automation", "Cargo management AI", "Maritime route optimization", "Safety compliance monitoring", "AI lead generation for maritime clients", "Sales automation for shipping services", "Customer service chatbots for maritime inquiries"]
            },
            "market_research": {
                "pain_points": ["data collection automation", "survey management", "analysis reporting", "client presentation preparation"],
                "solutions": ["Data collection AI", "Survey automation systems", "Research analysis automation", "Presentation preparation AI", "AI lead generation for research clients", "Sales automation for market research", "Customer service chatbots for research inquiries"]
            },
            "marketing_and_advertising": {
                "pain_points": ["campaign performance tracking", "customer segmentation", "content creation workflows", "ROI measurement"],
                "solutions": ["Campaign analytics AI", "Customer segmentation automation", "Content creation workflows", "Marketing ROI analytics", "AI lead generation for marketing clients", "Sales automation for advertising services", "Customer service chatbots for campaign inquiries"]
            },
            "mechanical_or_industrial_engineering": {
                "pain_points": ["design optimization", "project management", "quality control", "resource allocation"],
                "solutions": ["Engineering design optimization", "Engineering project management", "Quality control automation", "Resource allocation AI", "AI lead generation for engineering projects", "Sales automation for engineering services", "Customer service chatbots for technical specifications"]
            },
            "media_production": {
                "pain_points": ["content scheduling", "production workflow", "asset management", "distribution tracking"],
                "solutions": ["Content scheduling automation", "Production workflow AI", "Media asset management", "Distribution tracking systems", "AI lead generation for media clients", "Sales automation for production services", "Customer service chatbots for media inquiries"]
            },
            "medical_devices": {
                "pain_points": ["regulatory compliance", "quality control testing", "inventory management", "customer training"],
                "solutions": ["Medical device compliance automation", "Quality control AI", "Medical inventory management", "Training automation systems", "AI lead generation for medical clients", "Sales automation for device sales", "Customer service chatbots for device support"]
            },
            "medical_practice": {
                "pain_points": ["patient scheduling", "medical record management", "insurance processing", "appointment follow-ups"],
                "solutions": ["Patient scheduling automation", "Medical record AI", "Insurance processing automation", "Appointment follow-up systems", "AI lead generation for patient acquisition", "Sales automation for medical services", "Customer service chatbots for patient inquiries"]
            },
            "mental_health_care": {
                "pain_points": ["patient appointment scheduling", "treatment plan tracking", "insurance claim processing", "crisis intervention coordination"],
                "solutions": ["Mental health scheduling automation", "Treatment tracking AI", "Insurance claim automation", "Crisis intervention systems", "AI lead generation for mental health patients", "Sales automation for therapy services", "Customer service chatbots for mental health support"]
            },
            "military": {
                "pain_points": ["personnel management", "equipment tracking", "mission planning", "security compliance"],
                "solutions": ["Personnel management AI", "Equipment tracking automation", "Mission planning systems", "Military security compliance", "AI lead generation for defense contracts", "Sales automation for military services", "Customer service chatbots for military specifications"]
            },
            "mining_and_metals": {
                "pain_points": ["safety monitoring", "equipment maintenance", "production optimization", "environmental compliance"],
                "solutions": ["Mining safety AI", "Equipment maintenance automation", "Production optimization systems", "Environmental compliance tracking", "AI lead generation for mining clients", "Sales automation for mining equipment", "Customer service chatbots for mining support"]
            },
            "museums_and_institutions": {
                "pain_points": ["visitor engagement", "collection management", "event coordination", "educational program tracking"],
                "solutions": ["Visitor engagement AI", "Collection management automation", "Event coordination systems", "Educational program tracking", "AI lead generation for museum visitors", "Sales automation for museum programs", "Customer service chatbots for museum inquiries"]
            },
            "music": {
                "pain_points": ["royalty tracking", "distribution management", "fan engagement", "performance scheduling"],
                "solutions": ["Royalty tracking automation", "Music distribution AI", "Fan engagement analytics", "Performance scheduling systems", "AI lead generation for music promotion", "Sales automation for music sales", "Customer service chatbots for music inquiries"]
            },
            "nanotechnology": {
                "pain_points": ["research data management", "quality control", "regulatory compliance", "production scaling"],
                "solutions": ["Research data AI", "Nanotechnology quality control", "Regulatory compliance automation", "Production scaling systems", "AI lead generation for nanotech partnerships", "Sales automation for research collaborations", "Customer service chatbots for technical support"]
            },
            "nonprofit_organization_management": {
                "pain_points": ["donor management", "volunteer coordination", "program tracking", "fundraising automation"],
                "solutions": ["Donor management AI", "Volunteer coordination systems", "Program tracking automation", "Fundraising automation", "AI lead generation for donors", "Sales automation for fundraising campaigns", "Customer service chatbots for nonprofit inquiries"]
            },
            "oil_and_energy": {
                "pain_points": ["production monitoring", "safety compliance", "equipment maintenance", "market price tracking"],
                "solutions": ["Production monitoring AI", "Energy safety compliance", "Equipment maintenance automation", "Energy market analytics", "AI lead generation for energy clients", "Sales automation for energy services", "Customer service chatbots for energy inquiries"]
            },
            "online_media": {
                "pain_points": ["content management", "audience engagement", "ad revenue optimization", "performance analytics"],
                "solutions": ["Content management AI", "Audience engagement analytics", "Ad revenue optimization", "Media performance tracking", "AI lead generation for online audiences", "Sales automation for digital advertising", "Customer service chatbots for media support"]
            },
            "outsourcing/offshoring": {
                "pain_points": ["project coordination", "quality assurance", "communication management", "performance tracking"],
                "solutions": ["Project coordination AI", "Quality assurance automation", "Communication management systems", "Performance tracking analytics", "AI lead generation for outsourcing clients", "Sales automation for outsourcing services", "Customer service chatbots for project updates"]
            },
            "package/freight_delivery": {
                "pain_points": ["route optimization", "package tracking", "delivery scheduling", "customer communication"],
                "solutions": ["Delivery route optimization", "Package tracking automation", "Delivery scheduling AI", "Customer communication automation", "AI lead generation for shipping clients", "Sales automation for delivery services", "Customer service chatbots for package tracking"]
            },
            "packaging_and_containers": {
                "pain_points": ["inventory management", "production optimization", "quality control", "customer order fulfillment"],
                "solutions": ["Packaging inventory AI", "Production optimization systems", "Quality control automation", "Order fulfillment automation", "AI lead generation for packaging clients", "Sales automation for packaging sales", "Customer service chatbots for packaging inquiries"]
            },
            "paper_and_forest_products": {
                "pain_points": ["production optimization", "quality control", "supply chain management", "environmental compliance"],
                "solutions": ["Paper production optimization", "Quality control AI", "Forest supply chain management", "Environmental compliance tracking", "AI lead generation for paper clients", "Sales automation for paper products", "Customer service chatbots for product specifications"]
            },
            "performing_arts": {
                "pain_points": ["performance scheduling", "ticket sales management", "artist coordination", "venue optimization"],
                "solutions": ["Performance scheduling automation", "Ticket sales AI", "Artist coordination systems", "Venue optimization algorithms", "AI lead generation for performing arts audiences", "Sales automation for ticket sales", "Customer service chatbots for performance inquiries"]
            },
            "pharmaceuticals": {
                "pain_points": ["drug development tracking", "regulatory compliance", "quality control", "supply chain management"],
                "solutions": ["Drug development AI", "Pharmaceutical compliance automation", "Quality control systems", "Pharma supply chain optimization", "AI lead generation for pharmaceutical partnerships", "Sales automation for drug sales", "Customer service chatbots for pharmaceutical inquiries"]
            },
            "philanthropy": {
                "pain_points": ["donor relationship management", "grant tracking", "impact measurement", "fundraising coordination"],
                "solutions": ["Donor relationship AI", "Grant tracking automation", "Impact measurement systems", "Fundraising coordination", "AI lead generation for philanthropic donors", "Sales automation for charitable giving", "Customer service chatbots for philanthropy inquiries"]
            },
            "photography": {
                "pain_points": ["client booking management", "image organization", "editing workflow", "portfolio management"],
                "solutions": ["Photography booking automation", "Image organization AI", "Editing workflow optimization", "Portfolio management systems", "AI lead generation for photography clients", "Sales automation for photography services", "Customer service chatbots for booking inquiries"]
            },
            "plastics": {
                "pain_points": ["production optimization", "quality control", "inventory management", "environmental compliance"],
                "solutions": ["Plastics production optimization", "Quality control automation", "Plastics inventory management", "Environmental compliance tracking", "AI lead generation for plastics clients", "Sales automation for plastic products", "Customer service chatbots for product specifications"]
            },
            "political_organization": {
                "pain_points": ["voter outreach", "campaign management", "fundraising coordination", "policy tracking"],
                "solutions": ["Voter outreach automation", "Campaign management AI", "Political fundraising systems", "Policy tracking automation", "AI lead generation for political engagement", "Sales automation for political campaigns", "Customer service chatbots for political inquiries"]
            },
            "primary/secondary_education": {
                "pain_points": ["student performance tracking", "parent communication", "curriculum planning", "administrative tasks"],
                "solutions": ["Student performance analytics", "Parent communication automation", "Curriculum planning AI", "Administrative task automation", "AI lead generation for educational programs", "Sales automation for school enrollment", "Customer service chatbots for school inquiries"]
            },
            "printing": {
                "pain_points": ["order management", "production scheduling", "quality control", "inventory tracking"],
                "solutions": ["Print order management", "Production scheduling AI", "Printing quality control", "Print inventory tracking", "AI lead generation for printing clients", "Sales automation for print services", "Customer service chatbots for print orders"]
            },
            "professional_training_and_coaching": {
                "pain_points": ["client progress tracking", "scheduling coordination", "curriculum development", "performance measurement"],
                "solutions": ["Client progress AI", "Training scheduling automation", "Curriculum development systems", "Performance measurement analytics", "AI lead generation for training clients", "Sales automation for coaching services", "Customer service chatbots for training inquiries"]
            },
            "public_policy": {
                "pain_points": ["policy research", "stakeholder engagement", "impact analysis", "compliance tracking"],
                "solutions": ["Policy research AI", "Stakeholder engagement automation", "Policy impact analysis", "Compliance tracking systems", "AI lead generation for policy stakeholders", "Sales automation for policy services", "Customer service chatbots for policy inquiries"]
            },
            "public_relations_and_communications": {
                "pain_points": ["media monitoring", "campaign management", "client communication", "crisis management"],
                "solutions": ["Media monitoring AI", "PR campaign automation", "Client communication systems", "Crisis management automation", "AI lead generation for PR clients", "Sales automation for PR services", "Customer service chatbots for PR inquiries"]
            },
            "public_safety": {
                "pain_points": ["emergency response coordination", "resource allocation", "incident tracking", "community communication"],
                "solutions": ["Emergency response AI", "Resource allocation optimization", "Incident tracking automation", "Community communication systems", "AI lead generation for safety services", "Sales automation for safety solutions", "Customer service chatbots for safety inquiries"]
            },
            "publishing": {
                "pain_points": ["manuscript management", "distribution coordination", "marketing automation", "royalty tracking"],
                "solutions": ["Manuscript management AI", "Publishing distribution automation", "Publishing marketing systems", "Royalty tracking automation", "AI lead generation for publishing clients", "Sales automation for book sales", "Customer service chatbots for publishing inquiries"]
            },
            "railroad_manufacture": {
                "pain_points": ["production scheduling", "quality control", "safety compliance", "maintenance tracking"],
                "solutions": ["Railroad production optimization", "Quality control automation", "Railroad safety compliance", "Maintenance tracking systems", "AI lead generation for railroad clients", "Sales automation for railroad equipment", "Customer service chatbots for railroad support"]
            },
            "ranching": {
                "pain_points": ["livestock tracking", "feed management", "health monitoring", "market price tracking"],
                "solutions": ["Livestock tracking AI", "Feed management automation", "Animal health monitoring", "Ranching market analytics", "AI lead generation for livestock buyers", "Sales automation for livestock sales", "Customer service chatbots for ranching inquiries"]
            },
            "real_estate": {
                "pain_points": ["property listing management", "client relationship tracking", "market analysis", "transaction coordination"],
                "solutions": ["Property listing automation", "Real estate CRM", "Market analysis AI", "Transaction coordination systems", "AI lead generation for property leads", "Sales automation for real estate", "Customer service chatbots for property inquiries"]
            },
            "recreational_facilities_and_services": {
                "pain_points": ["facility booking", "member management", "equipment maintenance", "activity scheduling"],
                "solutions": ["Facility booking automation", "Member management AI", "Equipment maintenance tracking", "Activity scheduling systems", "AI lead generation for recreational members", "Sales automation for facility memberships", "Customer service chatbots for facility inquiries"]
            },
            "religious_institutions": {
                "pain_points": ["member engagement", "event coordination", "donation tracking", "communication management"],
                "solutions": ["Member engagement analytics", "Religious event coordination", "Donation tracking automation", "Religious communication systems", "AI lead generation for community outreach", "Sales automation for religious programs", "Customer service chatbots for religious inquiries"]
            },
            "renewables_and_environment": {
                "pain_points": ["energy production monitoring", "environmental compliance", "equipment maintenance", "sustainability reporting"],
                "solutions": ["Renewable energy monitoring", "Environmental compliance automation", "Green equipment maintenance", "Sustainability reporting AI", "AI lead generation for renewable clients", "Sales automation for green energy", "Customer service chatbots for environmental inquiries"]
            },
            "research": {
                "pain_points": ["data collection", "analysis automation", "project coordination", "publication management"],
                "solutions": ["Research data collection AI", "Analysis automation systems", "Research project coordination", "Publication management automation", "AI lead generation for research partnerships", "Sales automation for research services", "Customer service chatbots for research inquiries"]
            },
            "restaurants": {
                "pain_points": ["inventory waste and food costs", "staff scheduling conflicts", "long wait times during peak hours", "inconsistent customer service"],
                "solutions": ["AI inventory management that predicts demand and reduces waste", "Smart scheduling that optimizes staff based on predicted traffic", "Kitchen workflow AI that coordinates orders", "Automated customer feedback analysis", "AI lead generation for catering events", "Sales automation for repeat customers", "Customer service chatbots for reservations"]
            },
            "retail": {
                "pain_points": ["inventory management", "customer experience optimization", "sales forecasting", "staff scheduling"],
                "solutions": ["Retail inventory AI", "Customer experience analytics", "Sales forecasting systems", "Retail staff scheduling", "AI lead generation for retail customers", "Sales automation for retail promotions", "Customer service chatbots for shopping assistance"]
            },
            "security_and_investigations": {
                "pain_points": ["threat detection", "incident response", "client reporting", "surveillance monitoring"],
                "solutions": ["Threat detection AI", "Incident response automation", "Security reporting systems", "Surveillance monitoring automation", "AI lead generation for security clients", "Sales automation for security services", "Customer service chatbots for security inquiries"]
            },
            "semiconductors": {
                "pain_points": ["production yield optimization", "quality control", "supply chain management", "equipment maintenance"],
                "solutions": ["Semiconductor production optimization", "Quality control automation", "Semiconductor supply chain management", "Equipment maintenance AI", "AI lead generation for semiconductor clients", "Sales automation for chip sales", "Customer service chatbots for technical specifications"]
            },
            "sporting_goods": {
                "pain_points": ["inventory management", "seasonal demand forecasting", "customer preference tracking", "supply chain coordination"],
                "solutions": ["Sporting goods inventory AI", "Seasonal demand forecasting", "Customer preference analytics", "Sports supply chain optimization", "AI lead generation for sports customers", "Sales automation for sporting goods", "Customer service chatbots for product recommendations"]
            },
            "sports": {
                "pain_points": ["performance analytics", "fan engagement", "ticket sales management", "facility optimization"],
                "solutions": ["Sports performance AI", "Fan engagement analytics", "Ticket sales automation", "Sports facility optimization", "AI lead generation for sports fans", "Sales automation for sports marketing", "Customer service chatbots for sports inquiries"]
            },
            "staffing_and_recruiting": {
                "pain_points": ["candidate screening", "client matching", "interview scheduling", "performance tracking"],
                "solutions": ["AI candidate screening", "Client-candidate matching", "Interview scheduling automation", "Recruiting performance analytics", "AI lead generation for staffing clients", "Sales automation for recruiting services", "Customer service chatbots for staffing inquiries"]
            },
            "telecommunications": {
                "pain_points": ["network monitoring", "customer service volume", "service optimization", "infrastructure maintenance"],
                "solutions": ["Network monitoring AI", "Telecom customer service automation", "Service optimization systems", "Infrastructure maintenance automation", "AI lead generation for telecom clients", "Sales automation for telecom services", "Customer service chatbots for technical support"]
            },
            "textiles": {
                "pain_points": ["production optimization", "quality control", "inventory management", "supply chain coordination"],
                "solutions": ["Textile production optimization", "Quality control automation", "Textile inventory management", "Textile supply chain optimization", "AI lead generation for textile clients", "Sales automation for textile sales", "Customer service chatbots for textile inquiries"]
            },
            "think_tanks": {
                "pain_points": ["research coordination", "policy analysis", "publication management", "stakeholder engagement"],
                "solutions": ["Research coordination AI", "Policy analysis automation", "Publication management systems", "Stakeholder engagement analytics", "AI lead generation for policy stakeholders", "Sales automation for research services", "Customer service chatbots for policy inquiries"]
            },
            "tobacco": {
                "pain_points": ["regulatory compliance", "quality control", "inventory management", "market analysis"],
                "solutions": ["Tobacco compliance automation", "Quality control systems", "Tobacco inventory management", "Tobacco market analytics", "AI lead generation for tobacco distributors", "Sales automation for tobacco products", "Customer service chatbots for compliance inquiries"]
            },
            "translation_and_localization": {
                "pain_points": ["project management", "quality assurance", "client communication", "resource allocation"],
                "solutions": ["Translation project management", "Quality assurance automation", "Client communication systems", "Translation resource optimization", "AI lead generation for translation clients", "Sales automation for language services", "Customer service chatbots for translation inquiries"]
            },
            "transportation/trucking/railroad": {
                "pain_points": ["route optimization", "fleet management", "maintenance scheduling", "compliance tracking"],
                "solutions": ["Transportation route optimization", "Fleet management AI", "Transportation maintenance automation", "Transportation compliance tracking", "AI lead generation for transportation clients", "Sales automation for shipping services", "Customer service chatbots for shipment tracking"]
            },
            "utilities": {
                "pain_points": ["grid management", "customer service", "maintenance scheduling", "regulatory compliance"],
                "solutions": ["Utility grid management AI", "Utility customer service automation", "Utility maintenance scheduling", "Utility compliance tracking", "AI lead generation for utility customers", "Sales automation for utility services", "Customer service chatbots for utility inquiries"]
            },
            "venture_capital_and_private_equity": {
                "pain_points": ["deal sourcing", "due diligence", "portfolio management", "investor relations"],
                "solutions": ["Deal sourcing AI", "Due diligence automation", "Portfolio management systems", "Investor relations automation", "AI lead generation for investment opportunities", "Sales automation for fund raising", "Customer service chatbots for investor inquiries"]
            },
            "veterinary": {
                "pain_points": ["appointment scheduling", "medical record management", "inventory management", "client communication"],
                "solutions": ["Veterinary scheduling automation", "Veterinary medical records", "Veterinary inventory management", "Pet owner communication systems", "AI lead generation for pet owners", "Sales automation for veterinary services", "Customer service chatbots for pet care inquiries"]
            },
            "warehousing": {
                "pain_points": ["inventory tracking", "order fulfillment", "space optimization", "staff scheduling"],
                "solutions": ["Warehouse inventory AI", "Order fulfillment automation", "Warehouse space optimization", "Warehouse staff scheduling", "AI lead generation for warehousing clients", "Sales automation for warehouse services", "Customer service chatbots for inventory inquiries"]
            },
            "wholesale": {
                "pain_points": ["inventory management", "order processing", "client relationship management", "pricing optimization"],
                "solutions": ["Wholesale inventory AI", "Order processing automation", "Wholesale CRM systems", "Pricing optimization algorithms", "AI lead generation for wholesale buyers", "Sales automation for wholesale orders", "Customer service chatbots for wholesale inquiries"]
            },
            "wine_and_spirits": {
                "pain_points": ["inventory management", "distribution tracking", "compliance monitoring", "customer preference analysis"],
                "solutions": ["Wine inventory management", "Distribution tracking automation", "Alcohol compliance monitoring", "Customer preference analytics", "AI lead generation for wine customers", "Sales automation for wine sales", "Customer service chatbots for wine recommendations"]
            },
            "wireless": {
                "pain_points": ["network optimization", "customer service", "device management", "coverage analysis"],
                "solutions": ["Wireless network optimization", "Wireless customer service automation", "Device management systems", "Coverage analysis AI", "AI lead generation for wireless customers", "Sales automation for wireless services", "Customer service chatbots for wireless support"]
            },
            "writing_and_editing": {
                "pain_points": ["project management", "client communication", "quality control", "deadline tracking"],
                "solutions": ["Writing project management", "Client communication automation", "Editing quality control", "Deadline tracking systems", "AI lead generation for writing clients", "Sales automation for writing services", "Customer service chatbots for writing inquiries"]
            }
        }
        
        if pd.notna(industry) and industry.strip() and industry.lower() != 'your industry':
            # Industry-specific personalized content - NO FALLBACKS
            guidance = industry_guidance.get(industry.lower().replace(' ', '_').replace('&', 'and'))
            if not guidance:
                raise ValueError(f"Industry '{industry}' not found in guidance dictionary. Industry-specific content required.")
            pain_points = ", ".join(guidance["pain_points"][:3])
            solutions = guidance["solutions"]
            
            system_prompt_initial = """
Write exactly this format:

1. Start with: "Hey [name],"
2. Write 50-70 words about AI automation solutions for their industry  
3. End with one direct question asking if they want to discuss it
4. Use only standard letters, numbers, spaces, and punctuation marks
5. Write complete sentences in professional business tone

Example structure:
Hey [name], [industry context]. [solution description]. [specific benefit]. [direct question]?
"""
            
            user_prompt_initial = f"""
Write a natural, conversational cold email using this contact information:
---
{prospect_info}
---

Industry Context:
- They work in {industry} industry
- Common pain points: {pain_points}
- Our solutions: {', '.join(solutions)}

Write like you're a real person reaching out - natural, authentic, non-promotional tone.
Key guidelines:
- Start casually: "Hey {first_name}", "Hi {first_name}", "{first_name}, hope you're well"
- Mention you work with AI automation in a casual way.
- Reference their industry and mention 3 relevant pain points naturally
- Pick 3 of our solutions and COMPLETELY REPHRASE them in your own words - keep each solution explanation to 10-15 words max
- Keep it conversational and authentic.  
- Plain text only.
- 50-70 words max.
"""
        else:
            # Use template format for unknown industries
            user_prompt_initial = f"""
Use this exact template format, processing all spintext:

Hey {first_name}, {{{{hope you're good|hope all is well}}}}. I {{{{specialize in|work in}}}} AI automation and {{{{wanted to know|was just wondering}}}} if you've {{{{started using|taken advantage of}}}} any of the {{{{amazing things|cool stuff}}}} that AI {{{{can do|was built for}}}}.

{{{{In a nutshell|Put simply}}}}, we can {{{{automate|use AI to automate}}}} {{{{just about anything|pretty much anything}}}} {{{{you can imagine|your business needs|you or your team do}}}} - {{{{lead gen|lead generation|getting leads}}}}, {{{{closing deals|your sales cycle|making sales}}}}, customer {{{{support|service}}}}, {{{{appointment booking|scheduling}}}}, {{{{follow-ups|follow up sequences}}}}, you name it.

It's all {{{{hands-off|totally automated|completely hands-free}}}} once we {{{{set it up|get it running}}}}.

If {{{{you're interested|that sounds good|you want more info}}}}, let's {{{{schedule|get on|set up}}}} a quick {{{{call|meeting|Zoom call}}}} and I {{{{will show you everything|can show you how it works|will show you the magic}}}}. If not, {{{{all good|no problem|no worries}}}}.
"""

            system_prompt_initial = """
Process the spintext template:

1. Replace each {{option1|option2|option3}} with one random choice
2. End with one direct question 
3. Use only standard letters, numbers, spaces, and punctuation marks
4. Write complete sentences in conversational business tone
"""
        
        
        rate_limited_api_call()
        
        # Generate initial email - SIMPLIFIED
        completion_initial = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_initial},
                {"role": "user", "content": user_prompt_initial}
            ],
            temperature=0.0,
            max_tokens=200,
        )
        initial_email = completion_initial.choices[0].message.content.strip()
        # Single clean pass
        initial_email = nuclear_clean_email(initial_email)
        
        # STEP 2: Generate follow-up 1 - PURE PROMPT-BASED APPROACH
        
        # Always use industry-specific approach - NO FALLBACKS
        guidance = industry_guidance.get(industry.lower().replace(' ', '_').replace('&', 'and'))
        if not guidance:
            raise ValueError(f"Industry '{industry}' not found in guidance dictionary. Industry-specific content required.")
        pain_points = ", ".join(guidance["pain_points"][:3])
        solutions = guidance["solutions"]
        
        system_prompt_followup1 = """
Write exactly this format:

1. Start with: "Hey [name],"  
2. Write 60-75 words following up on AI automation solutions
3. End with one direct question about their interest
4. Use only standard letters, numbers, spaces, and punctuation marks
5. Write complete sentences in professional business tone

Example structure:
Hey [name], [follow-up context]. [solution reminder]. [value proposition]. [direct question]?
"""
        
        user_prompt_followup1 = f"""
Write a natural, conversational follow-up email using this contact information:
---
Contact: {first_name} at {company_name}
Industry: {industry}
---

Industry Context:
- They work in {industry} industry
- Common pain points: {pain_points}
- Our solutions: {', '.join(solutions)}

This is a follow-up to an unanswered cold email - DO NOT imply previous conversation.
Write like you're a real person reaching out - natural, authentic, non-promotional tone.
Key guidelines:
- Start casually with the prospect's name
- Mention you work with AI automation in a casual way
- Pick 3 of our solutions and COMPLETELY REPHRASE them in your own words - use different terminology, angles, and value propositions
- Keep it conversational and authentic
- Plain text only
- 60-75 words max
"""
        
        rate_limited_api_call()
        
        # Generate follow-up 1 - SIMPLIFIED
        completion_followup1 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_followup1},
                {"role": "user", "content": user_prompt_followup1}
            ],
            temperature=0.0,
            max_tokens=200,
        )
        followup_1_email = completion_followup1.choices[0].message.content.strip()
        # Single clean pass
        followup_1_email = nuclear_clean_email(followup_1_email)
        
        # STEP 3: Generate follow-up 2 - SIMPLIFIED
        system_prompt_followup2 = """
Write exactly this format:

1. Start with: "Hey [name],"
2. Write 50-70 words about wrapping up outreach respectfully
3. End with one direct statement about respecting their time
4. Use only standard letters, numbers, spaces, and punctuation marks
5. Write complete sentences in professional business tone

Example structure:
Hey [name], [acknowledgment of their busy schedule]. [respectful closing statement].
"""
        
        user_prompt_followup2 = f"""
Contact: {first_name} at {company_name}
Industry: {industry}

Write a final follow-up email acknowledging they are likely busy. State you will respect their time and stop contacting them unless they reach out.
"""
        
        rate_limited_api_call()
        
        # Generate follow-up 2 - SIMPLIFIED
        completion_followup2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_followup2},
                {"role": "user", "content": user_prompt_followup2}
            ],
            temperature=0.0,
            max_tokens=300,
        )
        followup_2_email = completion_followup2.choices[0].message.content.strip()
        # DOUBLE NUCLEAR CLEANING for followup_2 - The most problematic email
        followup_2_email = nuclear_clean_email(followup_2_email)
        followup_2_email = nuclear_clean_email(followup_2_email)  # Clean twice for safety
        
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



@celery_app.task(bind=True, max_retries=3, ignore_result=False)
def process_spreadsheet_task(self, file_path, job_id, mode="sequence"):
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
                
                # Always use the sequence function - it has the proper template logic
                result = generate_email_sequence_for_row_direct(row_data, index, job_id)
                
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
                flattened_row["initial_email"] = result.get("initial_email", "")
                flattened_row["followup_1"] = result.get("followup_1", "")  
                flattened_row["followup_2"] = result.get("followup_2", "")
                
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