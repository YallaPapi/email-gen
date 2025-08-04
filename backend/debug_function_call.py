#!/usr/bin/env python3

"""
Debug script to test which function is actually being called
and what prompts are being used.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_function_calls():
    """Test both functions to see their behavior"""
    
    # Test data
    test_row_data = {
        'first_name': 'John',
        'organization_name': 'Test Corp',
        'industry': 'technology'
    }
    
    print("=== TESTING FUNCTION IMPORTS ===")
    
    try:
        from tasks import process_single_email_direct
        print("✓ Successfully imported process_single_email_direct")
        
        # Check function source
        import inspect
        source = inspect.getsource(process_single_email_direct)
        print(f"✓ Function source length: {len(source)} characters")
        
        # Look for key prompts in the source
        if "if you're open to a chat, let me know - if not, all good" in source:
            print("✓ Found correct ending phrase in function source")
        else:
            print("✗ Correct ending phrase NOT found in function source")
            
        if "I'd love to chat" in source:
            print("✗ Found incorrect 'I'd love to chat' phrase in function source")
        else:
            print("✓ Incorrect phrase NOT found in function source")
            
    except ImportError as e:
        print(f"✗ Failed to import process_single_email_direct: {e}")
        return False
    
    print("\n=== TESTING CELERY TASK IMPORT ===")
    
    try:
        from tasks import process_single_email
        print("✓ Successfully imported process_single_email (Celery task)")
        
        # Check function source
        import inspect
        source = inspect.getsource(process_single_email)
        print(f"✓ Celery task source length: {len(source)} characters")
        
        # Look for key prompts in the source
        if "if you're open to a chat, let me know - if not, all good" in source:
            print("✓ Found correct ending phrase in Celery task source")
        else:
            print("✗ Correct ending phrase NOT found in Celery task source")
            
        if "I'd love to chat" in source:
            print("✗ Found incorrect 'I'd love to chat' phrase in Celery task source")
        else:
            print("✓ Incorrect phrase NOT found in Celery task source")
            
    except ImportError as e:
        print(f"✗ Failed to import process_single_email: {e}")
    
    print("\n=== TESTING ACTUAL FUNCTION EXECUTION ===")
    
    # Test the direct function call with a mock to see the prompt
    try:
        print("Testing process_single_email_direct execution...")
        
        # We'll patch the OpenAI client to see what prompt is sent
        from unittest.mock import Mock, patch
        
        mock_completion = Mock()
        mock_completion.choices[0].message.content = "Mock email response for testing"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        # Patch both the client and model assigner
        with patch('tasks.client', mock_client), \
             patch('tasks.model_assigner') as mock_assigner:
            
            mock_assigner.get_worker_model.return_value = "gpt-3.5-turbo"
            
            result = process_single_email_direct(test_row_data, 0, "test_job")
            
            # Check what was called
            if mock_client.chat.completions.create.called:
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args[1]['messages']  # keyword arguments
                
                print("✓ Function was called successfully")
                print(f"✓ Number of messages sent: {len(messages)}")
                
                # Check system prompt
                system_msg = messages[0]['content'] if messages[0]['role'] == 'system' else None
                user_msg = messages[1]['content'] if len(messages) > 1 and messages[1]['role'] == 'user' else None
                
                if system_msg:
                    print(f"✓ System prompt length: {len(system_msg)} characters")
                    if "if you're open to a chat, let me know - if not, all good" in system_msg:
                        print("✓ Found correct ending in system prompt")
                    else:
                        print("✗ Correct ending NOT found in system prompt")
                
                if user_msg:
                    print(f"✓ User prompt length: {len(user_msg)} characters")
                    if "if you're open to a chat, let me know - if not, all good" in user_msg:
                        print("✓ Found correct ending in user prompt")
                    else:
                        print("✗ Correct ending NOT found in user prompt")
                        
                    # Show first 200 chars of user prompt
                    print(f"✓ User prompt preview: {user_msg[:200]}...")
                
            else:
                print("✗ OpenAI client was not called")
                
    except Exception as e:
        print(f"✗ Error testing function execution: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== CHECKING FOR CONFLICTING IMPORTS ===")
    
    # Check if there are multiple tasks modules
    import importlib.util
    
    tasks_files = [
        'tasks.py',
        'tasks_original.py', 
        'tasks_broken.py'
    ]
    
    for task_file in tasks_files:
        if os.path.exists(task_file):
            print(f"Found tasks file: {task_file}")
            
            # Try to load and check if it has process_single_email_direct
            try:
                spec = importlib.util.spec_from_file_location("temp_tasks", task_file)
                temp_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(temp_module)
                
                if hasattr(temp_module, 'process_single_email_direct'):
                    func = getattr(temp_module, 'process_single_email_direct')
                    source = inspect.getsource(func)
                    
                    print(f"  - Has process_single_email_direct function")
                    
                    if "if you're open to a chat, let me know - if not, all good" in source:
                        print(f"  - ✓ Has correct ending phrase")
                    else:
                        print(f"  - ✗ Missing correct ending phrase")
                        
                    if "I'd love to chat" in source:
                        print(f"  - ✗ Has incorrect 'I'd love to chat' phrase")
                    else:
                        print(f"  - ✓ No incorrect phrase found")
                        
            except Exception as e:
                print(f"  - Error checking {task_file}: {e}")

if __name__ == "__main__":
    test_function_calls()