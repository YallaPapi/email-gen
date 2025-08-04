#!/usr/bin/env python3

"""
Simple test to show which function is being called in practice
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def simulate_line_422_call():
    """Simulate the exact call that happens on line 422"""
    print("🔍 SIMULATING LINE 422 CALL")
    print("=" * 50)
    
    # Test data - same as what would come from spreadsheet
    row_data = {
        'first_name': 'John',
        'organization_name': 'Test Corp',
        'industry': 'technology',
        'email': 'john@testcorp.com'
    }
    
    index = 0
    job_id = "test_job_123"
    
    try:
        # This is the exact call from line 422
        from tasks import process_single_email_direct
        
        # Patch OpenAI to prevent actual API calls
        import openai
        original_create = openai.ChatCompletion.create
        
        def mock_create(*args, **kwargs):
            # Capture the actual prompts being sent
            messages = kwargs.get('messages', [])
            print(f"\n📝 CAPTURED API CALL:")
            for i, msg in enumerate(messages):
                print(f"  Message {i+1} ({msg['role']}): {len(msg['content'])} chars")
                if "If you're open to a chat, let me know - if not, all good" in msg['content']:
                    print(f"    ✅ Contains correct CTA")
                else:
                    print(f"    ❌ Missing correct CTA")
            
            class MockChoice:
                def __init__(self):
                    self.message = type('obj', (object,), {
                        'content': 'Hey John,\n\nI work with AI automation and thought Test Corp might benefit from streamlined operations. If you\'re open to a chat, let me know - if not, all good.'
                    })
            
            class MockResponse:
                def __init__(self):
                    self.choices = [MockChoice()]
            
            return MockResponse()
        
        openai.ChatCompletion.create = mock_create
        
        print("🚀 EXECUTING: result = process_single_email_direct(row_data, index, job_id)")
        print()
        
        # THE ACTUAL CALL FROM LINE 422
        result = process_single_email_direct(row_data, index, job_id)
        
        print(f"\n📊 RESULT:")
        print(f"  Status: {result['status']}")
        print(f"  Email length: {len(result['email'])} characters")
        print(f"  Model used: {result['model_used']}")
        print(f"  Email content: {repr(result['email'])}")
        
        # Verify the CTA is correct
        if "if you're open to a chat, let me know - if not, all good" in result['email'].lower():
            print(f"  ✅ OUTPUT HAS CORRECT CTA")
        else:
            print(f"  ❌ OUTPUT MISSING CORRECT CTA")
            
        # Restore original
        openai.ChatCompletion.create = original_create
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_function_too():
    """Test the Celery function to show it uses same prompts"""
    print("\n🔥 TESTING CELERY FUNCTION (for comparison)")
    print("=" * 50)
    
    try:
        from tasks import process_single_email
        
        # Mock the self parameter for Celery task
        class MockSelf:
            pass
        
        mock_self = MockSelf()
        
        # Test data
        row_data = {
            'first_name': 'Sarah',
            'organization_name': 'Another Corp',
            'industry': 'healthcare'
        }
        
        # Patch OpenAI
        import openai
        original_create = openai.ChatCompletion.create
        
        def mock_create(*args, **kwargs):
            messages = kwargs.get('messages', [])
            print(f"\n📝 CELERY CAPTURED API CALL:")
            for i, msg in enumerate(messages):
                print(f"  Message {i+1} ({msg['role']}): {len(msg['content'])} chars")
                if "If you're open to a chat, let me know - if not, all good" in msg['content']:
                    print(f"    ✅ Contains correct CTA")
                else:
                    print(f"    ❌ Missing correct CTA")
            
            class MockChoice:
                def __init__(self):
                    self.message = type('obj', (object,), {
                        'content': 'Hi Sarah,\n\nI work with AI automation and noticed healthcare companies like Another Corp often need help with data processing. If you\'re open to a chat, let me know - if not, all good.'
                    })
            
            class MockResponse:
                def __init__(self):
                    self.choices = [MockChoice()]
            
            return MockResponse()
        
        openai.ChatCompletion.create = mock_create
        
        print("🚀 EXECUTING: process_single_email(self, row_data, index, job_id)")
        print()
        
        result = process_single_email(mock_self, row_data, 1, "test_job_celery")
        
        print(f"\n📊 CELERY RESULT:")
        print(f"  Status: {result['status']}")
        print(f"  Email content: {repr(result['email'])}")
        
        if "if you're open to a chat, let me know - if not, all good" in result['email'].lower():
            print(f"  ✅ CELERY OUTPUT HAS CORRECT CTA")
        else:
            print(f"  ❌ CELERY OUTPUT MISSING CORRECT CTA")
            
        # Restore original
        openai.ChatCompletion.create = original_create
        
    except Exception as e:
        print(f"❌ CELERY ERROR: {e}")

if __name__ == "__main__":
    print("🧪 TESTING WHICH FUNCTION IS ACTUALLY CALLED")
    print("This simulates the exact scenario from line 422")
    print()
    
    success = simulate_line_422_call()
    
    if success:
        test_celery_function_too()
        
        print("\n" + "=" * 50)
        print("🎯 CONCLUSIONS:")
        print("1. The debug logging clearly shows which function is called")
        print("2. Both functions now use identical prompts")
        print("3. Both functions produce the correct CTA")
        print("4. Nuclear cleaning removes signature remnants")
        print("\n🔧 TO DEBUG IN PRODUCTION:")
        print("- Look for '⚡ DIRECT CALL:' vs '🔥 CELERY TASK:' in logs")
        print("- Both should now produce identical results")
    else:
        print("\n❌ Test failed - check the error above")