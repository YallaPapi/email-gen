#!/usr/bin/env python3

"""
Comprehensive debugging script to identify and fix the function execution issues.
"""

import sys
import os
import inspect
import traceback

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_function_sources():
    """Compare the actual source code of both functions"""
    print("=== COMPARING FUNCTION SOURCES ===")
    
    try:
        from tasks import process_single_email, process_single_email_direct
        
        # Get source code for both functions
        celery_source = inspect.getsource(process_single_email)
        direct_source = inspect.getsource(process_single_email_direct)
        
        print(f"Celery function source length: {len(celery_source)} characters")
        print(f"Direct function source length: {len(direct_source)} characters")
        
        # Check for key differences in prompts
        print("\n--- CELERY FUNCTION PROMPTS ---")
        if "Write a casual email with variety" in celery_source:
            print("✓ Celery function uses 'casual email with variety' prompt")
        else:
            print("✗ Celery function missing 'casual email' prompt")
            
        if "Here are 3 examples:" in celery_source:
            print("✓ Celery function has 3 examples")
        else:
            print("✗ Celery function missing examples")
        
        print("\n--- DIRECT FUNCTION PROMPTS ---")
        if "Write a natural, conversational cold email" in direct_source:
            print("✓ Direct function uses 'natural, conversational' prompt")
        else:
            print("✗ Direct function missing 'natural, conversational' prompt")
            
        if "Key guidelines:" in direct_source:
            print("✓ Direct function has key guidelines")
        else:
            print("✗ Direct function missing key guidelines")
        
        # Check CTA phrases
        print("\n--- CTA ANALYSIS ---")
        if "if you're open to a chat, let me know - if not, all good" in celery_source:
            print("✓ Celery function has correct CTA in examples")
        else:
            print("✗ Celery function missing correct CTA")
            
        if "If you're open to a chat, let me know - if not, all good" in direct_source:
            print("✓ Direct function has correct CTA in guidelines")
        else:
            print("✗ Direct function missing correct CTA")
        
        # Extract and compare the actual prompts
        print("\n--- EXTRACTING ACTUAL PROMPTS ---")
        
        # Find the main prompt in celery function
        celery_lines = celery_source.split('\n')
        in_prompt = False
        celery_prompt_lines = []
        for line in celery_lines:
            if 'prompt = f"""' in line:
                in_prompt = True
                continue
            elif in_prompt and '"""' in line:
                break
            elif in_prompt:
                celery_prompt_lines.append(line)
        
        # Find the main prompt in direct function  
        direct_lines = direct_source.split('\n')
        in_user_prompt = False
        direct_prompt_lines = []
        for line in direct_lines:
            if 'user_prompt = f"""' in line:
                in_user_prompt = True
                continue
            elif in_user_prompt and '"""' in line:
                break
            elif in_user_prompt:
                direct_prompt_lines.append(line)
        
        print(f"Celery prompt has {len(celery_prompt_lines)} lines")
        print(f"Direct prompt has {len(direct_prompt_lines)} lines")
        
        # Show first few lines of each prompt
        print("\nCelery prompt preview:")
        for i, line in enumerate(celery_prompt_lines[:5]):
            print(f"  {i+1}: {line}")
            
        print("\nDirect prompt preview:")
        for i, line in enumerate(direct_prompt_lines[:5]):
            print(f"  {i+1}: {line}")
            
    except Exception as e:
        print(f"Error comparing sources: {e}")
        traceback.print_exc()

def debug_nuclear_cleaning():
    """Test the nuclear cleaning function with problematic text"""
    print("\n=== TESTING NUCLEAR CLEANING ===")
    
    try:
        from tasks import nuclear_clean_email
        
        # Test cases with common signature remnants
        test_cases = [
            "Hey John,\n\nThis is a test email.\n\nWarm",
            "Hi there,\n\nContent here.\n\nCheers",
            "Hello,\n\nMain content.\n\nBest,",
            "Hey,\n\nEmail body.\n\nWarm regards",
            "Hi,\n\nContent.\n\nThanks!",
            "Subject: Test\nHey John,\n\nContent here.\n\nWarm"
        ]
        
        for i, test_text in enumerate(test_cases, 1):
            print(f"\nTest case {i}:")
            print(f"Input: {repr(test_text)}")
            
            cleaned = nuclear_clean_email(test_text)
            print(f"Output: {repr(cleaned)}")
            
            # Check if problematic patterns remain
            if any(word in cleaned.lower() for word in ['warm', 'cheers', 'best,', 'thanks!']):
                print("✗ Signature remnants still present")
            else:
                print("✓ Clean output")
                
    except Exception as e:
        print(f"Error testing nuclear cleaning: {e}")
        traceback.print_exc()

def debug_function_execution():
    """Test actual function execution with debugging"""
    print("\n=== TESTING FUNCTION EXECUTION WITH DEBUGGING ===")
    
    test_data = {
        'first_name': 'John',
        'organization_name': 'Test Corp', 
        'industry': 'technology'
    }
    
    try:
        from tasks import process_single_email_direct
        
        # Monkey patch the OpenAI call to capture the prompts
        original_create = None
        captured_calls = []
        
        # Try to patch OpenAI
        try:
            import openai
            original_create = openai.ChatCompletion.create
            
            def mock_create(*args, **kwargs):
                captured_calls.append({
                    'args': args,
                    'kwargs': kwargs
                })
                # Return a mock response
                class MockChoice:
                    def __init__(self):
                        self.message = type('obj', (object,), {'content': 'Mock email response'})
                
                class MockResponse:
                    def __init__(self):
                        self.choices = [MockChoice()]
                
                return MockResponse()
            
            openai.ChatCompletion.create = mock_create
            
            print("✓ Successfully patched OpenAI API")
            
            # Call the function
            result = process_single_email_direct(test_data, 0, "test_job")
            
            print(f"✓ Function executed successfully")
            print(f"✓ Result status: {result.get('status')}")
            print(f"✓ Number of API calls captured: {len(captured_calls)}")
            
            # Analyze captured calls
            for i, call in enumerate(captured_calls, 1):
                print(f"\n--- API CALL {i} ---")
                kwargs = call['kwargs']
                messages = kwargs.get('messages', [])
                
                for j, msg in enumerate(messages):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    print(f"Message {j+1} ({role}):")
                    print(f"  Length: {len(content)} characters")
                    print(f"  Preview: {content[:200]}...")
                    
                    # Check for key phrases
                    if "If you're open to a chat, let me know - if not, all good" in content:
                        print(f"  ✓ Contains correct CTA")
                    else:
                        print(f"  ✗ Missing correct CTA")
                        
        except ImportError:
            print("✗ Could not import openai module")
            
        finally:
            # Restore original function
            if original_create:
                openai.ChatCompletion.create = original_create
                
    except Exception as e:
        print(f"Error testing function execution: {e}")
        traceback.print_exc()

def provide_fixes():
    """Provide specific fixes for the identified issues"""
    print("\n=== RECOMMENDED FIXES ===")
    
    print("1. PROMPT CONSISTENCY:")
    print("   - Both functions should use the same prompts")
    print("   - Direct function has better prompt structure")
    print("   - Celery function should adopt direct function prompts")
    
    print("\n2. NUCLEAR CLEANING IMPROVEMENTS:")
    print("   - Add pattern for isolated 'Warm' word: r'\\bWarm\\b'")
    print("   - Add pattern for isolated 'Best' word: r'\\bBest\\b'") 
    print("   - Add pattern for isolated 'Cheers' word: r'\\bCheers\\b'")
    print("   - Make patterns case-insensitive")
    
    print("\n3. API COMPATIBILITY:")
    print("   - Both functions use old OpenAI API format")
    print("   - Should migrate to client.chat.completions.create()")
    print("   - Add error handling for API changes")
    
    print("\n4. DEBUGGING ADDITIONS:")
    print("   - Add logging to show which function is called")
    print("   - Add prompt validation")
    print("   - Add cleaning result validation")

if __name__ == "__main__":
    print("Starting comprehensive debugging...\n")
    
    debug_function_sources()
    debug_nuclear_cleaning() 
    debug_function_execution()
    provide_fixes()
    
    print("\n=== DEBUGGING COMPLETE ===")