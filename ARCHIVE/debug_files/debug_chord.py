"""
Debugging utility for Celery chord failures
"""
import redis
import json
import pickle
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

def debug_chord_failure(job_id):
    """Debug a failed chord job by examining Redis backend"""
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    
    print(f"🔍 DEBUGGING CHORD FAILURE FOR JOB: {job_id}")
    print("=" * 60)
    
    # 1. Check progress counter
    progress_key = f"progress_{job_id}"
    progress = r.get(progress_key)
    print(f"Progress counter: {progress}")
    
    # 2. Get all task result keys
    task_keys = r.keys("celery-task-meta-*")
    print(f"Total Celery task results in Redis: {len(task_keys)}")
    
    # 3. Analyze task results
    successful_tasks = []
    failed_tasks = []
    malformed_tasks = []
    
    for key in task_keys:
        try:
            raw_result = r.get(key)
            if not raw_result:
                continue
            
            # Try to deserialize
            try:
                result_data = pickle.loads(raw_result)
            except:
                try:
                    result_data = json.loads(raw_result.decode('utf-8'))
                except:
                    malformed_tasks.append(key.decode('utf-8'))
                    continue
            
            # Check if this is an email task result
            if isinstance(result_data, dict) and 'result' in result_data:
                result = result_data['result']
                task_id = key.decode('utf-8').replace('celery-task-meta-', '')
                
                if isinstance(result, dict):
                    if 'row_data' in result or 'email' in result or 'initial_email' in result:
                        if result.get('status') == 'success':
                            successful_tasks.append((task_id, result))
                        else:
                            failed_tasks.append((task_id, result))
                else:
                    malformed_tasks.append((task_id, result))
                        
        except Exception as e:
            print(f"Error processing key {key}: {e}")
    
    print(f"✅ Successful tasks: {len(successful_tasks)}")
    print(f"❌ Failed tasks: {len(failed_tasks)}")
    print(f"🔧 Malformed tasks: {len(malformed_tasks)}")
    print()
    
    # 4. Show details of failed tasks
    if failed_tasks:
        print("FAILED TASK DETAILS:")
        print("-" * 40)
        for task_id, result in failed_tasks[:5]:  # Show first 5
            print(f"Task ID: {task_id[:8]}...")
            if isinstance(result, dict):
                print(f"  Status: {result.get('status', 'unknown')}")
                print(f"  Index: {result.get('index', 'unknown')}")
                if 'initial_email' in result:
                    email_preview = result['initial_email'][:100] + "..." if len(result['initial_email']) > 100 else result['initial_email']
                    print(f"  Email preview: {email_preview}")
                elif 'email' in result:
                    email_preview = result['email'][:100] + "..." if len(result['email']) > 100 else result['email']
                    print(f"  Email preview: {email_preview}")
            else:
                print(f"  Non-dict result: {type(result)} - {str(result)[:100]}...")
            print()
    
    # 5. Show malformed tasks
    if malformed_tasks:
        print("MALFORMED TASK DETAILS:")
        print("-" * 40)
        for item in malformed_tasks[:3]:  # Show first 3
            if isinstance(item, tuple):
                task_id, result = item
                print(f"Task ID: {task_id[:8]}...")
                print(f"  Result type: {type(result)}")
                print(f"  Result: {str(result)[:100]}...")
            else:
                print(f"Key: {item}")
            print()
    
    # 6. Recovery suggestions
    print("RECOVERY SUGGESTIONS:")
    print("-" * 40)
    if successful_tasks:
        print(f"✅ {len(successful_tasks)} tasks completed successfully - partial results available")
    
    if failed_tasks:
        print(f"❌ {len(failed_tasks)} tasks failed - check error messages above")
        
    if malformed_tasks:
        print(f"🔧 {len(malformed_tasks)} tasks returned malformed results - likely serialization issues")
    
    print("\nRecommended actions:")
    print("1. Check worker logs for detailed error messages")
    print("2. Verify OpenAI API key and rate limits")
    print("3. Check network connectivity to OpenAI")
    print("4. Monitor memory usage on workers")
    print("5. Consider reducing batch size if memory issues")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
        debug_chord_failure(job_id)
    else:
        print("Usage: python debug_chord.py <job_id>")