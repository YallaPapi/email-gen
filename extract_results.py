import pandas as pd

# Read the Excel file
df = pd.read_excel(r'C:\Users\stuar\Desktop\Projects\scalable_email_generator_fixed\uploads\result_bbb877f9-30de-45b6-abf9-847d2823bc52.xlsx')

print('**Initial Email 1 (Sarah Johnson):**')
print(df.iloc[0]['initial_email'])
print()

print('**Initial Email 2 (Dr. Michael Chen):**')
print(df.iloc[1]['initial_email'])
print()

print('**Initial Email 3 (Jennifer Martinez):**')
print(df.iloc[2]['initial_email'])
print()

print('---')
print()

print('**Follow-up Email 1 (Sarah Johnson):**')
print(df.iloc[0]['followup_1'])
print()

print('**Follow-up Email 2 (Dr. Michael Chen):**')
print(df.iloc[1]['followup_1'])
print()

print('**Follow-up Email 3 (Jennifer Martinez):**')
print(df.iloc[2]['followup_1'])