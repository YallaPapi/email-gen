"""
Test script to validate chord robustness improvements
"""
import pandas as pd
import sys
import os
import time
import requests

# Add backend to path
sys.path.append('backend')

def create_test_csv(filename, num_rows=5):
    """Create a small test CSV file"""
    data = []
    for i in range(num_rows):
        data.append({
            'first_name': f'Test{i}',
            'organization_name': f'Company{i}',
            'industry': 'Technology' if i % 2 == 0 else 'Marketing'
        })
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Created test CSV: {filename} with {num_rows} rows")

def test_sequence_generation():
    """Test email sequence generation with robust error handling"""
    
    # Create test file
    test_file = "test_emails.csv"
    create_test_csv(test_file, 3)  # Small test
    
    print("🧪 Testing robust chord implementation...")
    
    # Upload file
    try:
        with open(test_file, 'rb') as f:
            response = requests.post(
                "http://localhost:8000/upload",
                files={"file": f},
                data={"mode": "sequence"}
            )
        
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data['job_id']
            print(f"✅ Job submitted: {job_id}")
            
            # Monitor progress
            for i in range(60):  # 5 minutes max
                status_response = requests.get(f"http://localhost:8000/status/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"Status: {status['status']}, Progress: {status['progress']}/{status['total']}")
                    
                    if status['status'] in ['SUCCESS', 'PARTIAL', 'FAILURE']:
                        break
                        
                    # If failed, get debug info
                    if 'FAILED' in status['status'] or 'ERROR' in status['status']:
                        debug_response = requests.get(f"http://localhost:8000/debug/{job_id}")
                        if debug_response.status_code == 200:
                            debug_info = debug_response.json()
                            print("🔍 Debug info:")
                            print(f"  Task summary: {debug_info['task_summary']}")
                            if debug_info['task_details']:
                                print(f"  First failed task: {debug_info['task_details'][0]}")
                        break
                        
                time.sleep(5)
            
            # Final status check
            final_status = requests.get(f"http://localhost:8000/status/{job_id}")
            if final_status.status_code == 200:
                final_data = final_status.json()
                print(f"🎯 Final status: {final_data['status']}")
                
                # Try to download result
                if final_data.get('result_file') or 'SUCCESS' in final_data['status'] or 'PARTIAL' in final_data['status']:
                    download_response = requests.get(f"http://localhost:8000/download/{job_id}")
                    if download_response.status_code == 200:
                        with open("result_downloaded.xlsx", "wb") as f:
                            f.write(download_response.content)
                        print("✅ Result file downloaded successfully")
                        
                        # Check if result has expected structure
                        try:
                            df_result = pd.read_excel("result_downloaded.xlsx")
                            required_columns = ['initial_email', 'followup_1', 'followup_2', 'sequence_status']
                            missing_cols = [col for col in required_columns if col not in df_result.columns]
                            if not missing_cols:
                                print("✅ Result file has correct structure")
                                print(f"Generated sequences for {len(df_result)} rows")
                                
                                # Count successes
                                successful = len(df_result[df_result['sequence_status'] == 'success'])
                                print(f"✅ {successful}/{len(df_result)} sequences generated successfully")
                            else:
                                print(f"❌ Missing columns in result: {missing_cols}")
                        except Exception as e:
                            print(f"❌ Error reading result file: {e}")
                    else:
                        print(f"❌ Download failed: {download_response.status_code}")
                
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def test_error_scenarios():
    """Test various error scenarios to ensure robustness"""
    print("🧪 Testing error scenario handling...")
    
    # Test with malformed CSV
    malformed_csv = "malformed_test.csv"
    with open(malformed_csv, 'w') as f:
        f.write("invalid,csv,data\n")
        f.write("missing,fields\n")
        f.write("incomplete\n")
    
    try:
        with open(malformed_csv, 'rb') as f:
            response = requests.post(
                "http://localhost:8000/upload",
                files={"file": f},
                data={"mode": "sequence"}
            )
        
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data['job_id']
            print(f"Malformed CSV job: {job_id}")
            
            # Wait a bit and check if it handles gracefully
            time.sleep(10)
            
            debug_response = requests.get(f"http://localhost:8000/debug/{job_id}")
            if debug_response.status_code == 200:
                debug_info = debug_response.json()
                print(f"Malformed CSV handled: {debug_info['task_summary']}")
            
    except Exception as e:
        print(f"Malformed CSV test error: {e}")
    
    finally:
        if os.path.exists(malformed_csv):
            os.remove(malformed_csv)

if __name__ == "__main__":
    print("🚀 Starting chord robustness tests...")
    print("Make sure the backend server is running on localhost:8000")
    
    # Wait for user confirmation
    input("Press Enter to continue...")
    
    test_sequence_generation()
    test_error_scenarios()
    
    print("🎉 Tests completed!")