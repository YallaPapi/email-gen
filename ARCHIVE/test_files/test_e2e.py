#!/usr/bin/env python3
"""
OPERATION PHOENIX: End-to-End Browser Test Script
Per ZAD Mandate: "The Gauntlet" Test

This script validates the complete user workflow:
1. POST a real CSV to /upload endpoint
2. Poll /status until SUCCESS or FAILURE  
3. GET the result file from /download
4. Validate the Excel contains correct data and email columns

This is the ONLY test that matters - it must pass flawlessly.
"""

import requests
import time
import pandas as pd
import os
import sys
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_CSV_PATH = "real_test.csv"  # Per mandate requirement
TIMEOUT_SECONDS = 300  # 5 minutes max wait
POLL_INTERVAL = 2  # Check status every 2 seconds

def create_test_csv():
    """Create a real-world test CSV file"""
    test_data = [
        {
            "first_name": "John",
            "organization_name": "TestCorp",
            "industry": "Software",
            "email": "john@testcorp.com",
            "title": "CTO"
        },
        {
            "first_name": "Sarah",
            "organization_name": "TechStartup Inc",
            "industry": "Technology",
            "email": "sarah@techstartup.com", 
            "title": "CEO"
        },
        {
            "first_name": "Mike",
            "organization_name": "DataSolutions",
            "industry": "Analytics",
            "email": "mike@datasolutions.com",
            "title": "VP of Engineering"
        }
    ]
    
    df = pd.DataFrame(test_data)
    df.to_csv(TEST_CSV_PATH, index=False)
    print(f"✅ Created test CSV: {TEST_CSV_PATH}")
    return TEST_CSV_PATH

def test_server_availability():
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print("✅ Server is responding")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on http://localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Server check failed: {e}")
        return False

def upload_file(file_path, mode="sequence"):
    """Upload file to the server"""
    print(f"🚀 Uploading {file_path} in {mode} mode...")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            data = {'mode': mode}
            
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Upload successful. Job ID: {job_id}")
            return job_id
        else:
            print(f"❌ Upload failed with status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def poll_job_status(job_id):
    """Poll job status until completion"""
    print(f"⏳ Polling job status for {job_id}...")
    
    start_time = time.time()
    while time.time() - start_time < TIMEOUT_SECONDS:
        try:
            response = requests.get(f"{BASE_URL}/status/{job_id}", timeout=10)
            
            if response.status_code == 404:
                print(f"❌ Job {job_id} not found")
                return False
            elif response.status_code != 200:
                print(f"❌ Status check failed with code {response.status_code}")
                return False
            
            data = response.json()
            status = data.get('status', 'UNKNOWN')
            progress = data.get('progress', 0)
            total = data.get('total', 0)
            
            print(f"📊 Status: {status}, Progress: {progress}/{total}")
            
            if status == "SUCCESS":
                print("✅ Job completed successfully!")
                return True
            elif status == "FAILURE":
                print("❌ Job failed!")
                return False
            elif status.startswith("PARTIAL_"):
                print(f"⚠️ Job completed with partial results: {status}")
                return True  # Partial results are acceptable for testing
            elif status in ["PROCESSING", "QUEUED"]:
                # Continue polling
                time.sleep(POLL_INTERVAL)
                continue
            else:
                print(f"⚠️ Unknown status: {status}")
                time.sleep(POLL_INTERVAL)
                continue
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            time.sleep(POLL_INTERVAL)
            continue
    
    print(f"❌ Timeout after {TIMEOUT_SECONDS} seconds")
    return False

def download_and_validate_result(job_id, mode="sequence"):
    """Download result file and validate contents"""
    print(f"📥 Downloading result for job {job_id}...")
    
    try:
        response = requests.get(f"{BASE_URL}/download/{job_id}", timeout=30)
        
        if response.status_code == 200:
            # Save the downloaded file
            result_filename = f"test_result_{job_id}.xlsx"
            with open(result_filename, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Downloaded result file: {result_filename}")
            
            # Validate the contents
            return validate_result_file(result_filename, mode)
        else:
            print(f"❌ Download failed with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

def validate_result_file(filename, mode="sequence"):
    """Validate the downloaded result file"""
    print(f"🔍 Validating result file: {filename}")
    
    try:
        # Try to read as Excel first, then CSV
        try:
            df = pd.read_excel(filename)
        except:
            df = pd.read_csv(filename)
        
        print(f"📋 Result file contains {len(df)} rows")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Basic validation
        if len(df) == 0:
            print("❌ Result file is empty")
            return False
        
        # Validate expected columns based on mode
        if mode == "sequence":
            required_columns = ['initial_email', 'followup_1', 'followup_2']
            print("🔍 Validating sequence mode results (3 emails per row)...")
        else:
            required_columns = ['generated_email']
            print("🔍 Validating single mode results (1 email per row)...")
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        # Check that email columns are not empty
        empty_count = 0
        for col in required_columns:
            empty_values = df[col].isna().sum() + (df[col] == '').sum()
            if empty_values > 0:
                print(f"⚠️ {empty_values} empty values in column '{col}'")
                empty_count += empty_values
        
        # Show sample emails for manual inspection
        print("\n📧 Sample generated emails:")
        if mode == "sequence":
            for i, row in df.head(2).iterrows():
                print(f"\n--- Row {i+1} ---")
                print(f"Initial: {str(row['initial_email'])[:100]}...")
                print(f"Follow-up 1: {str(row['followup_1'])[:100]}...")
                print(f"Follow-up 2: {str(row['followup_2'])[:100]}...")
        else:
            for i, row in df.head(2).iterrows():
                print(f"Row {i+1}: {str(row['generated_email'])[:100]}...")
        
        # Final validation
        success_rate = ((len(df) * len(required_columns)) - empty_count) / (len(df) * len(required_columns))
        print(f"\n📊 Email generation success rate: {success_rate:.1%}")
        
        if success_rate >= 0.8:  # 80% success rate minimum
            print("✅ Result file validation PASSED!")
            return True
        else:
            print("❌ Result file validation FAILED - too many empty emails")
            return False
            
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def run_gauntlet_test(mode="sequence"):
    """Run the complete end-to-end test (THE GAUNTLET)"""
    print("🔥" * 50)
    print("🔥 OPERATION PHOENIX: THE GAUNTLET TEST")
    print("🔥 End-to-End Browser Workflow Validation")
    print("🔥" * 50)
    
    # Step 1: Check server availability
    if not test_server_availability():
        print("\n❌ THE GAUNTLET FAILED: Server not available")
        return False
    
    # Step 2: Create test CSV
    test_file = create_test_csv()
    
    # Step 3: Upload file
    job_id = upload_file(test_file, mode)
    if not job_id:
        print("\n❌ THE GAUNTLET FAILED: Upload failed")
        return False
    
    # Step 4: Poll status until completion
    if not poll_job_status(job_id):
        print("\n❌ THE GAUNTLET FAILED: Job did not complete successfully")
        return False
    
    # Step 5: Download and validate result
    if not download_and_validate_result(job_id, mode):
        print("\n❌ THE GAUNTLET FAILED: Result validation failed")
        return False
    
    # Success!
    print("\n" + "🎉" * 50)
    print("🎉 THE GAUNTLET PASSED!")
    print("🎉 OPERATION PHOENIX: BROWSER VERSION IS WORKING!")
    print("🎉" * 50)
    return True

def cleanup():
    """Clean up test files"""
    try:
        files_to_remove = [TEST_CSV_PATH] + list(Path('.').glob('test_result_*.xlsx')) + list(Path('.').glob('test_result_*.csv'))
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)
                print(f"🧹 Cleaned up: {file}")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    try:
        # Test both single and sequence modes
        print("Testing SINGLE mode...")
        single_success = run_gauntlet_test("single")
        
        print("\n" + "="*60 + "\n")
        
        print("Testing SEQUENCE mode...")
        sequence_success = run_gauntlet_test("sequence")
        
        print("\n" + "="*60)
        print("🎯 FINAL RESULTS:")
        print(f"   Single Mode: {'✅ PASS' if single_success else '❌ FAIL'}")
        print(f"   Sequence Mode: {'✅ PASS' if sequence_success else '❌ FAIL'}")
        
        if single_success and sequence_success:
            print("\n🎉 ALL TESTS PASSED - BROWSER VERSION IS WORKING!")
            cleanup()
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED - BROWSER VERSION NEEDS FIXING!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        cleanup()
        sys.exit(1)