#!/usr/bin/env python3
"""
Debug mode parameter handling
"""

import requests
import pandas as pd

def test_mode_parameter():
    """Test what happens to the mode parameter"""
    
    print("🔧 Mode Parameter Debug")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Create test file
    test_data = [{"first_name": "Bob", "organization_name": "DebugCorp", "industry": "Tech", "email": "bob@debug.com"}]
    df = pd.DataFrame(test_data)
    test_file = "mode_debug.csv"
    df.to_csv(test_file, index=False)
    
    try:
        # Test sequence mode
        print("📤 Testing mode='sequence'...")
        with open(test_file, 'rb') as f:
            files = {'file': f}
            data = {'mode': 'sequence'}
            response = requests.post(f"{base_url}/upload", files=files, data=data)
        
        print(f"Upload response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
            
            job_id = result['job_id']
            print(f"Job ID: {job_id}")
            
            # Check status immediately
            status_response = requests.get(f"{base_url}/status/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status data: {status_data}")
                print(f"Mode in status: {status_data.get('mode', 'NOT_FOUND')}")
            else:
                print(f"Status check failed: {status_response.status_code}")
        else:
            print(f"Upload failed: {response.text}")
            
        # Test single mode for comparison
        print("\n📤 Testing mode='single'...")
        with open(test_file, 'rb') as f:
            files = {'file': f}
            data = {'mode': 'single'}
            response = requests.post(f"{base_url}/upload", files=files, data=data)
        
        print(f"Upload response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
            
            job_id = result['job_id']
            print(f"Job ID: {job_id}")
            
            # Check status immediately
            status_response = requests.get(f"{base_url}/status/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status data: {status_data}")
                print(f"Mode in status: {status_data.get('mode', 'NOT_FOUND')}")
            else:
                print(f"Status check failed: {status_response.status_code}")
        else:
            print(f"Upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        import os
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_mode_parameter()