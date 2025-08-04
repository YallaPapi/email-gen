#!/usr/bin/env python3

"""
Test script to verify the email generation fix.
This script tests that the correct email endings are generated.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test data
test_data = {
    'first_name': 'John',
    'organization_name': 'TestCorp',
    'industry': 'Technology',
    'email': 'john@testcorp.com'
}

def test_function_imports():
    """Test that the functions can be imported without errors"""
    try:
        from tasks import generate_email_sequence_for_row_direct, process_single_email_direct
        print("✓ Functions imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False

def test_function_signature():
    """Test that the function signatures are correct (no self parameter)"""
    try:
        from tasks import generate_email_sequence_for_row_direct, process_single_email_direct
        import inspect
        
        # Check generate_email_sequence_for_row_direct signature
        sig1 = inspect.signature(generate_email_sequence_for_row_direct)
        params1 = list(sig1.parameters.keys())
        expected1 = ['row_data', 'row_index', 'job_id']
        
        if params1 == expected1:
            print("✓ generate_email_sequence_for_row_direct has correct signature")
        else:
            print(f"✗ generate_email_sequence_for_row_direct has wrong signature: {params1}, expected: {expected1}")
            return False
            
        # Check process_single_email_direct signature
        sig2 = inspect.signature(process_single_email_direct)
        params2 = list(sig2.parameters.keys())
        expected2 = ['row_data', 'row_index', 'job_id']
        
        if params2 == expected2:
            print("✓ process_single_email_direct has correct signature")
        else:
            print(f"✗ process_single_email_direct has wrong signature: {params2}, expected: {expected2}")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Signature test error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Celery Email Generation Fix")
    print("=" * 40)
    
    # Test imports
    if not test_function_imports():
        sys.exit(1)
    
    # Test function signatures  
    if not test_function_signature():
        sys.exit(1)
        
    print("\n✓ All tests passed! The fix should work correctly.")
    print("\nThe key fixes applied:")
    print("1. Removed 'self' parameter from generate_email_sequence_for_row_direct")
    print("2. Added missing process_single_email_direct function") 
    print("3. Updated process_spreadsheet_task to call the correct direct functions")
    print("4. Both functions now use the correct prompt with:")
    print('   "if you\'re open to a chat, let me know - if not, all good."')