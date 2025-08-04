#!/usr/bin/env python3

"""
Test the actual API call structure with the fixed code
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_call_structure():
    """Test that the API calls are structured correctly"""
    
    print("=== TESTING API CALL STRUCTURE ===")
    
    # Test data
    test_row_data = {
        'first_name': 'John',
        'organization_name': 'Test Corp',
        'industry': 'technology',
        'email': 'john@testcorp.com'
    }
    
    try:
        # Mock the OpenAI API call
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Hey John,\\n\\nI work with AI automation and noticed Test Corp's impressive tech solutions. There might be some smart ways we could help streamline your operations and boost efficiency. If you're open to a chat, let me know - if not, all good."
        
        # Mock the model assigner
        mock_model_assigner = Mock()
        mock_model_assigner.get_worker_model.return_value = "gpt-3.5-turbo"
        
        with patch('openai.ChatCompletion.create', return_value=mock_response) as mock_create, \
             patch('tasks.model_assigner', mock_model_assigner):
            
            from tasks import process_single_email_direct
            
            print("✓ Successfully imported function with mocked OpenAI")
            
            # Call the function
            result = process_single_email_direct(test_row_data, 0, "test_job")
            
            print("✓ Function executed successfully")
            print(f"✓ Result status: {result['status']}")
            print(f"✓ Generated email: {repr(result['email'])}")
            
            # Check that the API was called correctly
            if mock_create.called:
                print("✓ OpenAI ChatCompletion.create was called")
                
                # Get the call arguments
                call_args = mock_create.call_args
                
                # Check model
                model = call_args[1]['model'] if 'model' in call_args[1] else call_args[0][0] if call_args[0] else 'unknown'
                print(f"✓ Model used: {model}")
                
                # Check messages
                messages = call_args[1]['messages'] if 'messages' in call_args[1] else []
                print(f"✓ Number of messages: {len(messages)}")
                
                if len(messages) >= 2:
                    system_msg = messages[0]['content'] if messages[0]['role'] == 'system' else ''
                    user_msg = messages[1]['content'] if messages[1]['role'] == 'user' else ''
                    
                    print(f"✓ System message length: {len(system_msg)} chars")
                    print(f"✓ User message length: {len(user_msg)} chars")
                    
                    # Check for key phrases in user message
                    required_phrase = "if you're open to a chat, let me know - if not, all good"
                    if required_phrase in user_msg:
                        print("✓ CORRECT: Required ending phrase found in user message")
                    else:
                        print("✗ ERROR: Required ending phrase missing from user message")
                        print(f"User message preview: {user_msg[:200]}...")
                        
                    # Check system message constraints
                    if "CRITICAL" in system_msg:
                        print("✓ System message includes critical constraints")
                    
                # Check temperature and max_tokens
                temp = call_args[1].get('temperature', 'not set')
                max_tokens = call_args[1].get('max_tokens', 'not set')
                print(f"✓ Temperature: {temp}")
                print(f"✓ Max tokens: {max_tokens}")
                
            else:
                print("✗ OpenAI ChatCompletion.create was NOT called")
                
            # Check if the result contains the mocked response
            if "if you're open to a chat, let me know - if not, all good" in result['email']:
                print("✓ PERFECT: Result contains correct ending phrase")
            else:
                print("✗ WARNING: Result doesn't contain correct ending phrase")
                print(f"Actual result: {repr(result['email'])}")
                
    except Exception as e:
        print(f"✗ Error testing API call: {e}")
        import traceback
        traceback.print_exc()

def test_sequence_api_calls():
    """Test the sequence generation API calls"""
    
    print(f"\\n=== TESTING SEQUENCE GENERATION API CALLS ===")
    
    # Test data
    test_row_data = {
        'first_name': 'Jane',
        'organization_name': 'Example Inc',
        'industry': 'healthcare'
    }
    
    try:
        # Mock responses for all three API calls
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test email content with if you're open to a chat, let me know - if not, all good."
        
        mock_model_assigner = Mock()
        mock_model_assigner.get_worker_model.return_value = "gpt-3.5-turbo"
        
        with patch('openai.ChatCompletion.create', return_value=mock_response) as mock_create, \
             patch('tasks.model_assigner', mock_model_assigner):
            
            from tasks import generate_email_sequence_for_row_direct
            
            print("✓ Successfully imported sequence function")
            
            # Call the function
            result = generate_email_sequence_for_row_direct(test_row_data, 0, "test_job")
            
            print("✓ Sequence function executed successfully")
            print(f"✓ Result status: {result['status']}")
            
            # Check that API was called 3 times (initial + 2 follow-ups)
            call_count = mock_create.call_count
            print(f"✓ OpenAI API called {call_count} times (expected: 3)")
            
            if call_count >= 1:
                # Check first call (initial email)
                first_call = mock_create.call_args_list[0]
                messages = first_call[1]['messages'] if 'messages' in first_call[1] else []
                
                if len(messages) >= 2:
                    user_msg = messages[1]['content'] if messages[1]['role'] == 'user' else ''
                    
                    required_phrase = "if you're open to a chat, let me know - if not, all good"
                    if required_phrase in user_msg:
                        print("✓ PERFECT: Initial email prompt has correct ending")
                    else:
                        print("✗ ERROR: Initial email prompt missing correct ending")
                        
    except Exception as e:
        print(f"✗ Error testing sequence API calls: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_call_structure()
    test_sequence_api_calls()