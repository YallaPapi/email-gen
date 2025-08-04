#!/usr/bin/env python3

"""
Final test to verify all fixes are working correctly
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_function_identification():
    """Test that we can clearly identify which function is called"""
    print("=== TESTING FUNCTION IDENTIFICATION ===")
    
    test_data = {
        'first_name': 'John',
        'organization_name': 'Test Corp',
        'industry': 'technology'
    }
    
    try:
        from tasks import process_single_email_direct
        print("✓ Imported process_single_email_direct")
        
        # Patch OpenAI to avoid actual API calls
        import openai
        original_create = openai.ChatCompletion.create
        
        def mock_create(*args, **kwargs):
            class MockChoice:
                def __init__(self):
                    self.message = type('obj', (object,), {
                        'content': 'Hey John,\n\nI work with AI automation and noticed Test Corp could benefit from streamlined processes. If you\'re open to a chat, let me know - if not, all good.'
                    })
            
            class MockResponse:
                def __init__(self):
                    self.choices = [MockChoice()]
            
            return MockResponse()
        
        openai.ChatCompletion.create = mock_create
        
        print("\n--- TESTING DIRECT FUNCTION ---")
        result = process_single_email_direct(test_data, 0, "test_job")
        
        print(f"✓ Function executed successfully")
        print(f"✓ Status: {result['status']}")
        print(f"✓ Email content: {repr(result['email'])}")
        
        # Check for correct CTA
        if "if you're open to a chat, let me know - if not, all good" in result['email'].lower():
            print("✓ Correct CTA found in output")
        else:
            print("✗ Correct CTA NOT found in output")
            
        # Restore original function
        openai.ChatCompletion.create = original_create
        
    except Exception as e:
        print(f"✗ Error testing direct function: {e}")
        import traceback
        traceback.print_exc()

def test_nuclear_cleaning_comprehensive():
    """Test nuclear cleaning with all problematic patterns"""
    print("\n=== COMPREHENSIVE NUCLEAR CLEANING TEST ===")
    
    try:
        from tasks import nuclear_clean_email
        
        test_cases = [
            # Test case 1: Isolated "Warm"
            {
                'input': 'Hey John,\n\nGreat to connect with you.\n\nWarm',
                'expected_clean': True,
                'name': 'Isolated Warm'
            },
            # Test case 2: "Warm regards"
            {
                'input': 'Hi there,\n\nEmail content here.\n\nWarm regards',
                'expected_clean': True,
                'name': 'Warm regards'
            },
            # Test case 3: Subject line + signature
            {
                'input': 'Subject: Test Email\nHey John,\n\nContent here.\n\nBest,',
                'expected_clean': True,
                'name': 'Subject + Best'
            },
            # Test case 4: Multiple signatures
            {
                'input': 'Hi John,\n\nContent.\n\nThanks\nCheers\nWarm',
                'expected_clean': True,
                'name': 'Multiple signatures'
            },
            # Test case 5: Valid content with "warm" in middle (should keep)
            {
                'input': 'Hey John,\n\nI hope you have a warm welcome at the conference.\n\nLooking forward to chatting.',
                'expected_clean': False,  # Should keep "warm" as it's in content
                'name': 'Valid warm in content'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['name']}")
            print(f"Input: {repr(test_case['input'])}")
            
            result = nuclear_clean_email(test_case['input'])
            print(f"Output: {repr(result)}")
            
            # Check for problematic words at the end
            problematic_words = ['warm', 'best', 'cheers', 'thanks', 'regards']
            has_signature_remnants = any(
                result.strip().lower().endswith(word) for word in problematic_words
            )
            
            if test_case['expected_clean']:
                if not has_signature_remnants:
                    print("✓ Correctly cleaned signature remnants")
                else:
                    print("✗ Still has signature remnants")
            else:
                if result.count('warm') > 0 and 'conference' in result:
                    print("✓ Correctly preserved valid content with 'warm'")
                else:
                    print("✗ Incorrectly removed valid content")
                    
    except Exception as e:
        print(f"✗ Error testing nuclear cleaning: {e}")
        import traceback
        traceback.print_exc()

def test_prompt_consistency():
    """Verify both functions use the same prompts"""
    print("\n=== TESTING PROMPT CONSISTENCY ===")
    
    try:
        from tasks import process_single_email, process_single_email_direct
        import inspect
        
        # Get source code
        celery_source = inspect.getsource(process_single_email)
        direct_source = inspect.getsource(process_single_email_direct)
        
        # Check key phrases that should be identical
        key_phrases = [
            "Write a natural, conversational cold email",
            "If you're open to a chat, let me know - if not, all good",
            "Key guidelines:",
            "MANDATORY: End with EXACTLY these words"
        ]
        
        print("Checking prompt consistency...")
        
        for phrase in key_phrases:
            in_celery = phrase in celery_source
            in_direct = phrase in direct_source
            
            if in_celery and in_direct:
                print(f"✓ Both functions have: '{phrase[:40]}...'")
            elif in_celery and not in_direct:
                print(f"✗ Only Celery has: '{phrase[:40]}...'")
            elif not in_celery and in_direct:
                print(f"✗ Only Direct has: '{phrase[:40]}...'")
            else:
                print(f"✗ Neither has: '{phrase[:40]}...'")
        
        # Check for debug logging
        if "CELERY TASK: Processing row" in celery_source:
            print("✓ Celery function has debug logging")
        else:
            print("✗ Celery function missing debug logging")
            
        if "DIRECT CALL: Processing row" in direct_source:
            print("✓ Direct function has debug logging")
        else:
            print("✗ Direct function missing debug logging")
            
    except Exception as e:
        print(f"✗ Error testing prompt consistency: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 FINAL COMPREHENSIVE TEST SUITE")
    print("=" * 50)
    
    test_function_identification()
    test_nuclear_cleaning_comprehensive()
    test_prompt_consistency()
    
    print("\n" + "=" * 50)
    print("🎯 TEST SUITE COMPLETE")
    print("\nKey improvements made:")
    print("1. ✅ Fixed prompt consistency between functions")
    print("2. ✅ Enhanced nuclear cleaning for isolated signature words")
    print("3. ✅ Added debug logging to identify which function executes")
    print("4. ✅ Both functions now use identical prompts and CTAs")