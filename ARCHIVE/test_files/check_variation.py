#!/usr/bin/env python3
"""
Test script to check variation in follow-up emails
"""
import pandas as pd
import requests
import json
import time
import os

def test_variation():
    """Test that follow-up emails have good variation"""
    
    # Create test data with multiple people in same industry
    test_data = [
        {"first_name": "Mike", "organization_name": "TechCorp", "industry": "Software", "email": "mike@techcorp.com"},
        {"first_name": "Lisa", "organization_name": "DevSolutions", "industry": "Software", "email": "lisa@devsolutions.com"},
        {"first_name": "Tom", "organization_name": "CodeWorks", "industry": "Software", "email": "tom@codeworks.com"},
        {"first_name": "Emma", "organization_name": "SoftInc", "industry": "Software", "email": "emma@softinc.com"},
        {"first_name": "Alex", "organization_name": "DataFlow", "industry": "Software", "email": "alex@dataflow.com"}
    ]
    
    # Create CSV
    df = pd.DataFrame(test_data)
    test_file = "variation_test.csv"
    df.to_csv(test_file, index=False)
    print(f"✅ Created test file: {test_file}")
    
    # Upload file
    print("📤 Uploading variation test...")
    with open(test_file, 'rb') as f:
        files = {'file': f}
        data = {'mode': 'sequence'}
        response = requests.post('http://localhost:8000/upload', files=files, data=data)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return
    
    job_id = response.json()['job_id']
    print(f"✅ Upload successful! Job ID: {job_id}")
    
    # Monitor progress
    print("⏳ Monitoring progress...")
    max_wait = 120  # 2 minutes
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
                print("✅ Processing completed successfully!")
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
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        return
    
    result_file = f"variation_result_{job_id}.xlsx"
    with open(result_file, 'wb') as f:
        f.write(response.content)
    print(f"✅ Downloaded result to: {result_file}")
    
    # Analyze variation
    print("\n🔍 ANALYZING FOLLOW-UP VARIATION...")
    print("=" * 50)
    
    df_result = pd.read_excel(result_file)
    
    print(f"Generated emails for {len(df_result)} contacts in Software industry\n")
    
    # Check first follow-up variation
    print("📧 FOLLOW-UP 1 ANALYSIS:")
    print("-" * 30)
    followup1_emails = df_result['followup_1'].tolist()
    
    # Extract greetings (first 15 characters of each email)
    greetings = []
    for email in followup1_emails:
        if pd.notna(email):
            greeting = str(email)[:50].strip()
            greetings.append(greeting)
            print(f"• {greeting}")
    
    print(f"\nUnique greeting variations: {len(set(greetings))}/{len(greetings)}")
    
    # Check for repetitive phrases
    print("\n🔍 CHECKING FOR REPETITIVE PHRASES:")
    all_text = " ".join([str(email) for email in followup1_emails if pd.notna(email)])
    
    repetitive_phrases = [
        "Hey [name], hope you're good. Just wanted to shoot you this quick email",
        "with a little more info about how we would be able to help",
        "hope you're good",
        "shoot you this quick email"
    ]
    
    for phrase in repetitive_phrases:
        count = all_text.lower().count(phrase.lower())
        if count > 1:
            print(f"⚠️  '{phrase}' appears {count} times")
        else:
            print(f"✅ '{phrase}' appears {count} times")
    
    # Show sample emails
    print("\n📧 SAMPLE FOLLOW-UP EMAILS:")
    print("-" * 40)
    for i, row in df_result.iterrows():
        print(f"\n{i+1}. {row['first_name']} at {row['organization_name']}:")
        print(f"   {str(row['followup_1'])[:100]}...")
    
    # Cleanup
    os.remove(test_file)
    os.remove(result_file)
    print(f"\n🧹 Cleaned up test files")

if __name__ == "__main__":
    test_variation()