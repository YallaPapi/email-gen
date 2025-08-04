#!/usr/bin/env python3

"""
Simple test to verify function signatures without importing OpenAI dependencies.
"""

import ast
import sys

def check_function_signatures():
    """Parse the tasks.py file and check function signatures"""
    try:
        with open('tasks.py', 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        functions_found = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name in ['generate_email_sequence_for_row_direct', 'process_single_email_direct']:
                    args = [arg.arg for arg in node.args.args]
                    functions_found[node.name] = args
        
        # Check signatures
        expected_sig = ['row_data', 'row_index', 'job_id']
        
        success = True
        
        if 'generate_email_sequence_for_row_direct' in functions_found:
            actual = functions_found['generate_email_sequence_for_row_direct']
            if actual == expected_sig:
                print("✓ generate_email_sequence_for_row_direct has correct signature:", actual)
            else:
                print("✗ generate_email_sequence_for_row_direct has wrong signature:", actual, "expected:", expected_sig)
                success = False
        else:
            print("✗ generate_email_sequence_for_row_direct not found")
            success = False
            
        if 'process_single_email_direct' in functions_found:
            actual = functions_found['process_single_email_direct']
            if actual == expected_sig:
                print("✓ process_single_email_direct has correct signature:", actual)
            else:
                print("✗ process_single_email_direct has wrong signature:", actual, "expected:", expected_sig)
                success = False
        else:
            print("✗ process_single_email_direct not found")
            success = False
            
        return success
        
    except Exception as e:
        print(f"✗ Error checking signatures: {e}")
        return False

def check_correct_prompts():
    """Check that the correct prompt text is used"""
    try:
        with open('tasks.py', 'r') as f:
            content = f.read()
        
        # Check for the correct ending phrase
        correct_ending = 'if you\'re open to a chat, let me know - if not, all good'
        
        if correct_ending in content:
            print("✓ Found correct email ending phrase in code")
            count = content.count(correct_ending)
            print(f"  Found {count} occurrences of the correct ending")
            return True
        else:
            print("✗ Correct email ending phrase not found in code")
            print("  Expected:", correct_ending)
            return False
            
    except Exception as e:
        print(f"✗ Error checking prompts: {e}")
        return False

if __name__ == "__main__":
    print("Testing Celery Email Generation Fix")
    print("=" * 40)
    
    success = True
    
    if not check_function_signatures():
        success = False
    
    if not check_correct_prompts():
        success = False
    
    if success:
        print("\n✓ All checks passed! The fix looks correct.")
        print("\nSummary of fixes:")
        print("1. ✓ generate_email_sequence_for_row_direct has correct signature (no 'self')")
        print("2. ✓ process_single_email_direct function exists with correct signature")
        print("3. ✓ Code contains the correct email ending phrase")
    else:
        print("\n✗ Some issues found. Please review the fixes.")
        sys.exit(1)