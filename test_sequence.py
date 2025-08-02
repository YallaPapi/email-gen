#!/usr/bin/env python3
"""
Test script to verify email sequence generation works correctly.
This script simulates the sequence generation process to verify the fix.
"""

import requests
import time
import json
import pandas as pd
import os

def test_sequence_generation():
    """Test the email sequence generation with a small dataset"""
    
    # API endpoint
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Email Sequence Generation")
    print("=" * 50)
    
    # Test data - small dataset for quick testing
    test_data = [
        {"first_name": "John", "organization_name": "TechCorp", "industry": "Software", "email": "john@techcorp.com"},
        {"first_name": "Sarah", "organization_name": "HealthPlus", "industry": "Healthcare", "email": "sarah@healthplus.com"}
    ]
    
    # Create test CSV
    df = pd.DataFrame(test_data)
    test_file = "test_sequence_small.csv"
    df.to_csv(test_file, index=False)
    print(f"✅ Created test file: {test_file}")
    
    try:
        # Upload file with sequence mode
        print(f"📤 Uploading {test_file} with mode='sequence'...")
        
        with open(test_file, 'rb') as f:
            files = {'file': f}
            data = {'mode': 'sequence'}
            response = requests.post(f"{base_url}/upload", files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return False
            
        result = response.json()
        job_id = result['job_id']
        print(f"✅ Upload successful! Job ID: {job_id}")
        
        # Monitor progress
        print("⏳ Monitoring progress...")
        max_wait = 120  # 2 minutes max
        wait_time = 0
        
        while wait_time < max_wait:
            status_response = requests.get(f"{base_url}/status/{job_id}")
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code}")
                return False
                
            status_data = status_response.json()
            print(f"Status: {status_data['status']}, Progress: {status_data.get('progress', 0)}/{status_data.get('total', 0)}")
            
            if status_data['status'] == 'SUCCESS':
                print("✅ Processing completed successfully!")
                break
            elif status_data['status'] == 'FAILURE':
                print("❌ Processing failed!")
                return False
            elif status_data['status'].startswith('PARTIAL_'):
                print(f"⚠️ Partial completion: {status_data['status']}")
                break
            
            time.sleep(2)
            wait_time += 2
        
        if wait_time >= max_wait:
            print("⏰ Timeout waiting for completion")
            return False
        
        # Download and verify result
        print("📥 Downloading result...")
        download_response = requests.get(f"{base_url}/download/{job_id}")
        
        if download_response.status_code != 200:
            print(f"❌ Download failed: {download_response.status_code}")
            return False
        
        # Save and analyze result
        result_file = f"test_result_{job_id}.xlsx"
        with open(result_file, 'wb') as f:
            f.write(download_response.content)
        
        print(f"✅ Downloaded result to: {result_file}")
        
        # Verify columns
        print("🔍 Verifying result columns...")
        result_df = pd.read_excel(result_file)
        
        print(f"Columns found: {list(result_df.columns)}")
        print(f"Number of rows: {len(result_df)}")
        
        # Check for expected sequence columns
        expected_columns = ['initial_email', 'followup_1', 'followup_2']
        found_columns = [col for col in expected_columns if col in result_df.columns]
        missing_columns = [col for col in expected_columns if col not in result_df.columns]
        
        print(f"✅ Found sequence columns: {found_columns}")
        if missing_columns:
            print(f"❌ Missing sequence columns: {missing_columns}")
            return False
        
        # Check that emails were generated
        for idx, row in result_df.iterrows():
            print(f"\n--- Row {idx + 1}: {row['first_name']} ---")
            for col in expected_columns:
                email_content = row[col]
                if isinstance(email_content, str) and len(email_content) > 10 and not email_content.startswith('ERROR'):
                    print(f"✅ {col}: Generated ({len(email_content)} chars)")
                else:
                    print(f"❌ {col}: Failed or empty - {email_content}")
                    return False
        
        print("\n🎉 TEST PASSED! Email sequence generation is working correctly!")
        print(f"✅ Generated 3 emails per contact ({len(result_df)} contacts)")
        print(f"✅ All expected columns present: {expected_columns}")
        print(f"✅ All emails contain content")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        # Cleanup
        for f in [test_file, f"test_result_{job_id}.xlsx" if 'job_id' in locals() else None]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"🧹 Cleaned up: {f}")
                except:
                    pass

if __name__ == "__main__":
    success = test_sequence_generation()
    exit(0 if success else 1)