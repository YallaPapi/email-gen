import pandas as pd

# Read the Excel file
df = pd.read_excel(r'C:\Users\stuar\Desktop\Projects\scalable_email_generator_fixed\uploads\result_74eb2557-616f-4d68-98ec-7f3810f06036.xlsx')

print("Columns in the file:")
print(list(df.columns))
print()

if 'followup_2' in df.columns:
    print('=== HUMOROUS FOLLOW-UP 2 EMAILS ===\n')
    
    for i, row in df.iterrows():
        print(f'**Follow-up 2 Email {i+1} ({row["name"]}):**')
        print(row['followup_2'])
        print()
else:
    print("No followup_2 column found. Only these columns exist:")
    print(list(df.columns))