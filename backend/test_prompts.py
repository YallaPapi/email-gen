#!/usr/bin/env python3

"""
Test script to verify the exact prompts being used by the fixed functions
"""

import sys
import os
import inspect

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def extract_prompts_from_function():
    """Extract and verify the prompts from the actual function source"""
    
    print("=== VERIFYING PROMPTS IN FIXED FUNCTIONS ===")
    
    try:
        from tasks import process_single_email_direct
        
        # Get the function source
        source = inspect.getsource(process_single_email_direct)
        
        print(f"✓ Function source length: {len(source)} characters")
        
        # Extract the user_prompt content
        start_marker = 'user_prompt = f"""'
        end_marker = '"""'
        
        start_pos = source.find(start_marker)
        if start_pos != -1:
            start_pos += len(start_marker)
            end_pos = source.find(end_marker, start_pos)
            
            if end_pos != -1:
                prompt_content = source[start_pos:end_pos]
                
                print(f"✓ Found user prompt (length: {len(prompt_content)} chars)")
                print(f"\n=== USER PROMPT CONTENT ===")
                print(prompt_content)
                
                # Check for key phrases
                required_phrase = "if you're open to a chat, let me know - if not, all good"
                wrong_phrases = ["totally cool", "I'd love to chat", "totally fine"]
                
                if required_phrase in prompt_content:
                    print(f"\n✓ CORRECT: Found required ending phrase")
                else:
                    print(f"\n✗ ERROR: Missing required ending phrase")
                
                for wrong_phrase in wrong_phrases:
                    if wrong_phrase in prompt_content:
                        print(f"✗ ERROR: Found wrong phrase: '{wrong_phrase}'")
                    else:
                        print(f"✓ GOOD: No wrong phrase: '{wrong_phrase}'")
                        
            else:
                print("✗ Could not find end of user prompt")
        else:
            print("✗ Could not find user prompt in function")
            
        # Also check system prompt
        start_marker = 'system_prompt = """'
        start_pos = source.find(start_marker)
        if start_pos != -1:
            start_pos += len(start_marker)
            end_pos = source.find('"""', start_pos)
            
            if end_pos != -1:
                system_prompt = source[start_pos:end_pos]
                print(f"\n=== SYSTEM PROMPT CONTENT ===")
                print(system_prompt)
                
                # Check system prompt for key requirements
                if "CRITICAL: Do not include" in system_prompt:
                    print("✓ System prompt includes critical constraints")
                else:
                    print("? System prompt missing critical constraints")
                    
    except Exception as e:
        print(f"✗ Error analyzing function: {e}")
        import traceback
        traceback.print_exc()

def test_celery_task_prompts():
    """Test the Celery task version as well"""
    
    print(f"\n=== CHECKING CELERY TASK VERSION ===")
    
    try:
        from tasks import process_single_email
        
        # Get the function source
        source = inspect.getsource(process_single_email)
        
        print(f"✓ Celery task source length: {len(source)} characters")
        
        # Check for the example prompts in the Celery version
        if "If you're open to a chat, let me know - if not, all good" in source:
            print("✓ Celery task has correct ending in examples")
        else:
            print("✗ Celery task missing correct ending in examples")
            
        # Check for wrong phrases
        wrong_phrases = ["totally cool", "I'd love to chat", "totally fine"]
        for wrong_phrase in wrong_phrases:
            if wrong_phrase in source:
                print(f"✗ ERROR: Celery task contains wrong phrase: '{wrong_phrase}'")
            else:
                print(f"✓ GOOD: Celery task doesn't contain: '{wrong_phrase}'")
                
    except Exception as e:
        print(f"✗ Error analyzing Celery task: {e}")

def test_sequence_function():
    """Test the sequence generation function"""
    
    print(f"\n=== CHECKING SEQUENCE GENERATION FUNCTION ===")
    
    try:
        from tasks import generate_email_sequence_for_row_direct
        
        # Get the function source  
        source = inspect.getsource(generate_email_sequence_for_row_direct)
        
        print(f"✓ Sequence function source length: {len(source)} characters")
        
        # Check for correct ending phrase in initial email prompt
        required_phrase = "if you're open to a chat, let me know - if not, all good"
        if required_phrase in source:
            print("✓ Sequence function has correct ending phrase")
        else:
            print("✗ Sequence function missing correct ending phrase")
            
        # Count occurrences of the phrase (should appear in initial email prompt)
        count = source.count(required_phrase)
        print(f"✓ Required phrase appears {count} times in sequence function")
        
        # Check for wrong phrases
        wrong_phrases = ["totally cool", "I'd love to chat", "totally fine"]
        for wrong_phrase in wrong_phrases:
            if wrong_phrase in source:
                print(f"✗ ERROR: Sequence function contains wrong phrase: '{wrong_phrase}'")
            else:
                print(f"✓ GOOD: Sequence function doesn't contain: '{wrong_phrase}'")
                
    except Exception as e:
        print(f"✗ Error analyzing sequence function: {e}")

if __name__ == "__main__":
    extract_prompts_from_function()
    test_celery_task_prompts()
    test_sequence_function()