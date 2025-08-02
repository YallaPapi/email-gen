#!/usr/bin/env python3
"""
Debug the API calls to see what's actually happening
"""

import requests
import time
import pandas as pd
import json

def debug_api_calls():
    """Debug what's happening with the API"""
    
    print("🔧 API Debug Test")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Create a simple test file
    test_data = [{"first_name": "Alice", "organization_name": "TestCorp", "industry": "Tech", "email": "alice@test.com"}]
    df = pd.DataFrame(test_data)
    test_file = "debug_test.csv"
    df.to_csv(test_file, index=False)
    
    try:
        # Upload with sequence mode
        print("📤 Uploading with mode='sequence'...")
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'text/csv')}
            data = {'mode': 'sequence'}
            response = requests.post(f"{base_url}/upload", files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.text}")
            return
            
        result = response.json()
        job_id = result['job_id']
        print(f"✅ Job ID: {job_id}")
        
        # Monitor and get detailed status
        for i in range(30):  # 30 seconds max
            status_response = requests.get(f"{base_url}/status/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status check {i+1}: {status_data}")
                
                if status_data['status'] == 'SUCCESS':
                    break
                elif status_data['status'] == 'FAILURE':
                    print("❌ Job failed")
                    return
            time.sleep(1)
        
        # Try to download
        download_response = requests.get(f"{base_url}/download/{job_id}")
        if download_response.status_code == 200:
            result_file = f"debug_result_{job_id}.xlsx"
            with open(result_file, 'wb') as f:
                f.write(download_response.content)
            
            print(f"✅ Downloaded: {result_file}")
            
            # Analyze the result
            df_result = pd.read_excel(result_file)
            print(f"Result columns: {list(df_result.columns)}")
            
            # Print first row data
            if len(df_result) > 0:
                row = df_result.iloc[0]
                print(f"First row data:")
                for col, val in row.items():
                    if isinstance(val, str) and len(val) > 50:
                        print(f"  {col}: {val[:50]}... ({len(val)} chars)")
                    else:
                        print(f"  {col}: {val}")
            
            # Check if we have sequence columns
            sequence_cols = ['initial_email', 'followup_1', 'followup_2']
            has_sequence = all(col in df_result.columns for col in sequence_cols)
            
            print(f"\n🔍 Sequence columns present: {has_sequence}")
            if not has_sequence:
                print(f"❌ Expected: {sequence_cols}")
                print(f"❌ Found: {[col for col in df_result.columns if 'email' in col.lower()]}")
            
            # Cleanup
            import os
            os.remove(result_file)
            
        else:
            print(f"❌ Download failed: {download_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import os
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    debug_api_calls()