#\!/usr/bin/env python3
"""
Final test of template-free personalized follow-up emails
"""
import pandas as pd
import requests
import json
import time
import os

def final_test():
    """Test personalized follow-up emails"""
    
    # Create test data with 2 people in same industry to check variation
    test_data = [
        {"first_name": "Mike", "organization_name": "TechCorp", "industry": "Software", "email": "mike@techcorp.com"},
        {"first_name": "Lisa", "organization_name": "DevSolutions", "industry": "Software", "email": "lisa@devsolutions.com"}
    ]
    
    # Create CSV
    df = pd.DataFrame(test_data)
    test_file = "final_test.csv"
    df.to_csv(test_file, index=False)
    print(f"✅ Created test file: {test_file}")
    
    # Upload file
    print("📤 Uploading final test...")
    with open(test_file, 'rb') as f:
        files = {'file': f}
        data = {'mode': 'sequence'}
        response = requests.post('http://localhost:8000/upload', files=files, data=data)
    
    if response.status_code \!= 200:
        print(f"❌ Upload failed: {response.text}")
        return
    
    job_id = response.json()['job_id']
    print(f"✅ Upload successful\! Job ID: {job_id}")
    
    # Monitor progress
    print("⏳ Monitoring progress...")
    max_wait = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f'http://localhost:8000/status/{job_id}')
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get('status', 'UNKNOWN')
            progress = status_data.get('progress', 0)
            total = status_data.get('total', 0)
            
            print(f"Status: {status}, Progress: {progress}/{total}")
            
            if status == "SUCCESS":
                print("✅ Processing completed successfully\!")
                break
            elif status.startswith("FAILURE") or status.startswith("ERROR"):
                print(f"❌ Processing failed: {status}")
                return
        
        time.sleep(3)
    else:
        print("❌ Timeout waiting for processing to complete")
        return
    
    # Download result
    print("📥 Downloading result...")
    response = requests.get(f'http://localhost:8000/download/{job_id}')
    if response.status_code \!= 200:
        print(f"❌ Download failed: {response.status_code}")
        return
    
    result_file = f"final_result_{job_id}.xlsx"
    with open(result_file, 'wb') as f:
        f.write(response.content)
    print(f"✅ Downloaded result to: {result_file}")
    
    # Analyze results
    print("\n🔍 ANALYZING PERSONALIZATION...")
    print("=" * 60)
    
    df_result = pd.read_excel(result_file)
    
    for i, row in df_result.iterrows():
        print(f"\n👤 {row['first_name']} at {row['organization_name']}:")
        print(f"📧 FOLLOW-UP 1:")
        print(f"   {row['followup_1'][:100]}...")
        print(f"📧 FOLLOW-UP 2:")  
        print(f"   {row['followup_2'][:100]}...")
    
    # Check for template patterns
    print(f"\n🔍 CHECKING FOR TEMPLATES:")
    followup1_emails = [str(row['followup_1']) for _, row in df_result.iterrows()]
    
    template_phrases = [
        "Hey [name], hope you're good. Just wanted to shoot you this quick email",
        "with a little more info about how we would be able to help"
    ]
    
    for phrase in template_phrases:
        count = sum(1 for email in followup1_emails if phrase in email)
        if count > 0:
            print(f"❌ Template found: '{phrase}' appears {count} times")
        else:
            print(f"✅ No template: '{phrase}' not found")
    
    # Check uniqueness
    unique_starts = set()
    for email in followup1_emails:
        start = email[:50] if email else ""
        unique_starts.add(start)
    
    print(f"\n📊 UNIQUENESS: {len(unique_starts)}/{len(followup1_emails)} unique follow-up starts")
    
    if len(unique_starts) == len(followup1_emails):
        print("✅ All follow-up emails are unique\!")
    else:
        print("❌ Some follow-up emails are duplicated")
    
    # Cleanup
    os.remove(test_file)
    os.remove(result_file)
    print(f"\n🧹 Cleaned up test files")

if __name__ == "__main__":
    final_test()
EOF < /dev/null
