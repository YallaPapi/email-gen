#!/usr/bin/env python3
"""
Recovery script to salvage generated emails from Redis/Celery backend
when the combine step failed but emails were successfully generated
"""

import redis
import json
import pandas as pd
import pickle
from datetime import datetime
import os

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def recover_batch_results(job_id):
    """Recover all generated emails for a specific batch from Redis"""
    
    print(f"Recovering batch: {job_id}")
    
    # Get all Celery task result keys
    task_keys = redis_client.keys("celery-task-meta-*")
    print(f"Found {len(task_keys)} total task result keys in Redis")
    
    recovered_results = []
    success_count = 0
    error_count = 0
    
    for key in task_keys:
        try:
            # Get the raw result data
            raw_result = redis_client.get(key)
            if not raw_result:
                continue
                
            # Celery stores results as pickled data
            try:
                result_data = pickle.loads(raw_result)
            except:
                # Try JSON if pickle fails
                try:
                    result_data = json.loads(raw_result.decode('utf-8'))
                except:
                    continue
            
            # Check if this result contains email data
            if isinstance(result_data, dict) and 'result' in result_data:
                result = result_data['result']
                
                # Look for email generation results
                if isinstance(result, dict) and 'row_data' in result and 'email' in result:
                    recovered_results.append(result)
                    if result.get('status') == 'success':
                        success_count += 1
                    else:
                        error_count += 1
                    
                    if len(recovered_results) % 1000 == 0:
                        print(f"Recovered {len(recovered_results)} results so far...")
                        
        except Exception as e:
            continue
    
    print(f"Recovery complete: {len(recovered_results)} total results")
    print(f"Success: {success_count}, Errors: {error_count}")
    
    if not recovered_results:
        print("No recoverable results found. The data may have been cleaned up already.")
        return None
    
    # Sort by index to maintain order
    try:
        recovered_results.sort(key=lambda x: x.get('index', 0))
        print("Results sorted by original index")
    except:
        print("Warning: Could not sort results by index")
    
    return recovered_results

def save_recovered_results(results, job_id):
    """Save recovered results to Excel file"""
    
    if not results:
        print("No results to save")
        return None
    
    print(f"Building Excel file from {len(results)} recovered results...")
    
    final_data = []
    actual_success = 0
    
    for result in results:
        # Get the original row data
        row = result['row_data'].copy()
        
        # Clean the email text to remove problematic characters
        email_text = result['email']
        if isinstance(email_text, str):
            # Remove problematic characters that Excel can't handle
            email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
            # Remove other control characters
            email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
        
        # Add the cleaned generated email
        row['generated_email'] = email_text
        row['model_used'] = result.get('model_used', 'unknown')
        row['recovery_status'] = result.get('status', 'unknown')
        
        final_data.append(row)
        
        if result.get('status') == 'success' and not str(result['email']).startswith('ERROR'):
            actual_success += 1
    
    # Create DataFrame and save
    df = pd.DataFrame(final_data)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"uploads/RECOVERED_{job_id}_{timestamp}.csv"
    
    # Save as CSV to avoid Excel character issues
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"Recovered data saved to: {output_file}")
    print(f"Total rows: {len(final_data)}")
    print(f"Successful emails: {actual_success}")
    print(f"Success rate: {(actual_success/len(final_data)*100):.1f}%")
    
    return output_file

def main():
    job_id = "47ef53d4-3301-4d0b-bcf0-8493c4be0582"
    
    print("=" * 60)
    print("BATCH RECOVERY SCRIPT")
    print("=" * 60)
    
    # Check if we can connect to Redis
    try:
        redis_client.ping()
        print("✓ Connected to Redis")
    except:
        print("✗ Cannot connect to Redis. Make sure it's running on localhost:6379")
        return
    
    # Check progress counter
    progress_key = f"progress_{job_id}"
    progress = redis_client.get(progress_key)
    if progress:
        print(f"✓ Found progress counter: {progress.decode()} emails processed")
    else:
        print("! No progress counter found - data may have been cleaned up")
    
    # Recover the results
    results = recover_batch_results(job_id)
    
    if results:
        # Save to Excel
        output_file = save_recovered_results(results, job_id)
        
        if output_file:
            print("\n" + "=" * 60)
            print("RECOVERY SUCCESSFUL!")
            print(f"File saved: {output_file}")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("RECOVERY FAILED - No data found")
        print("The results may have already been cleaned up from Redis")
        print("=" * 60)

if __name__ == "__main__":
    main()