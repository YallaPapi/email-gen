import pandas as pd

# Read the results
df = pd.read_excel('result_chord_fix_test.xlsx')

print('Columns:', list(df.columns))
print(f'\nGenerated {len(df)} email sequences')
print('\n--- FOLLOW-UP 1 SAMPLES ---')

for i, row in df.iterrows():
    print(f'\n{row["organization_name"]} ({row["industry"]}):')
    print(f'{row["followup_1"]}')
    print('-' * 50)