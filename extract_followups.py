import pandas as pd

# Read the Excel file
df = pd.read_excel(r'C:\Users\stuar\Desktop\Projects\scalable_email_generator_fixed\uploads\result_de659539-a93f-4ae4-b617-2b1eda9f97f4.xlsx')

print('=== FIRST FOLLOW-UP EMAILS FOR ALL 3 HEALTHCARE RECIPIENTS ===\n')

for i, row in df.iterrows():
    print(f'RECIPIENT {i+1}:')
    print(f'Name: {row["name"]}')
    print(f'Company: {row["company"]}')
    print(f'Role: {row["role"]}')
    print(f'Email: {row["email"]}')
    print(f'\nFIRST FOLLOW-UP EMAIL:')
    print(row['followup_1'])
    print('\n' + '='*80 + '\n')