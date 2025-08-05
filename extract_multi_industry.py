import pandas as pd

# Read the Excel file
df = pd.read_excel(r'C:\Users\stuar\Desktop\Projects\scalable_email_generator_fixed\uploads\result_d45e8ffb-501b-4627-8672-0db27bca4de5.xlsx')

print('=== MULTI-INDUSTRY EMAIL GENERATION TEST ===\n')

industries = df['industry'].unique()
print(f"Industries tested: {', '.join(industries)}\n")

# Group by industry and show emails
for industry in industries:
    industry_data = df[df['industry'] == industry]
    print(f"=== {industry.upper()} INDUSTRY ===\n")
    
    for i, row in industry_data.iterrows():
        print(f"**{row['name']} - {row['role']} at {row['company']}**")
        print(f"Initial Email:")
        print(row['initial_email'])
        print()
        print(f"Follow-up 1:")
        print(row['followup_1'])
        print()
        print(f"Follow-up 2:")
        print(row['followup_2'])
        print('\n' + '='*80 + '\n')

print("\n=== UNIQUENESS ANALYSIS ===")
print("Checking for repeated phrases across industries...\n")

# Check for common phrases
all_initials = df['initial_email'].tolist()
all_followups1 = df['followup_1'].tolist()
all_followups2 = df['followup_2'].tolist()

print("Initial email openings:")
for i, email in enumerate(all_initials):
    opening = email.split('.')[0] if '.' in email else email[:50]
    print(f"{i+1}. {opening}...")

print("\nFollow-up 1 openings:")  
for i, email in enumerate(all_followups1):
    opening = email.split('.')[0] if '.' in email else email[:50]
    print(f"{i+1}. {opening}...")