#!/usr/bin/env python3
"""
Debug script to see full email content
"""
import pandas as pd
import requests
import json
import time
import os

def debug_full_emails():
    """Test and show full email content"""
    
    # Create test data with one person
    test_data = [
        {"first_name": "John", "organization_name": "TestCorp", "industry": "Software", "email": "john@testcorp.com"}
    ]
    
    # Create CSV
    df = pd.DataFrame(test_data)
    test_file = "debug_test.csv"
    df.to_csv(test_file, index=False)
    print(f"✅ Created test file: {test_file}")
    
    # Upload file
    print("📤 Uploading debug test...")
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
                print("✅ Processing completed successfully!")
                break
            elif status.startswith("FAILURE") or status.startswith("ERROR"):
                print(f"❌ Processing failed: {status}")
                return
        
        time.sleep(2)
    else:
        print("❌ Timeout waiting for processing to complete")
        return
    
    # Download result
    print("📥 Downloading result...")
    response = requests.get(f'http://localhost:8000/download/{job_id}')
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        return
    
    result_file = f"debug_result_{job_id}.xlsx"
    with open(result_file, 'wb') as f:
        f.write(response.content)
    print(f"✅ Downloaded result to: {result_file}")
    
    # Show full emails
    print("\n📧 FULL EMAIL CONTENT:")
    print("=" * 60)
    
    df_result = pd.read_excel(result_file)
    row = df_result.iloc[0]
    
    print(f"INITIAL EMAIL:")
    print(f"'{row['initial_email']}'")
    print(f"\nFOLLOW-UP 1:")
    print(f"'{row['followup_1']}'")
    print(f"\nFOLLOW-UP 2:")  
    print(f"'{row['followup_2']}'")
    
    # Cleanup
    os.remove(test_file)
    os.remove(result_file)
    print(f"\n🧹 Cleaned up test files")

if __name__ == "__main__":
    debug_full_emails()