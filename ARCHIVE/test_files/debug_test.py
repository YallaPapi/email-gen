#!/usr/bin/env python3
"""
Debug test to see what's happening with the sequence generation
"""

import pandas as pd
import sys
import os

# Add backend to path
sys.path.append('backend')

from tasks import process_email_sequence, combine_sequence_results

def test_direct_sequence():
    """Test the sequence generation directly without the web interface"""
    
    print("🔧 Direct Sequence Test")
    print("=" * 50)
    
    # Test data
    test_row = {
        "first_name": "John", 
        "organization_name": "TechCorp", 
        "industry": "Software", 
        "email": "john@techcorp.com"
    }
    
    job_id = "debug_test_123"
    
    print("Testing process_email_sequence directly...")
    
    try:
        # Call the sequence function directly
        result = process_email_sequence(test_row, 0, job_id)
        
        print(f"✅ process_email_sequence result keys: {list(result.keys())}")
        
        # Check what was returned
        expected_keys = ['initial_email', 'followup_1', 'followup_2', 'status', 'index', 'row_data', 'model_used']
        for key in expected_keys:
            if key in result:
                if key.endswith('_email'):
                    content = result[key]
                    print(f"✅ {key}: {'Generated' if len(str(content)) > 10 else 'Empty/Error'} ({len(str(content))} chars)")
                else:
                    print(f"✅ {key}: {result[key]}")
            else:
                print(f"❌ Missing key: {key}")
        
        # Test combine function
        print("\nTesting combine_sequence_results...")
        
        results = [result]  # List of one result
        combine_result = combine_sequence_results(results, job_id, 1)
        
        print(f"✅ combine_sequence_results status: {combine_result['status']}")
        
        # Check the file
        result_file = f"uploads/result_{job_id}.xlsx"
        if os.path.exists(result_file):
            print(f"✅ Result file created: {result_file}")
            
            # Check columns
            df = pd.read_excel(result_file)
            print(f"Columns in result: {list(df.columns)}")
            
            expected_columns = ['initial_email', 'followup_1', 'followup_2']
            for col in expected_columns:
                if col in df.columns:
                    content = df[col].iloc[0] if len(df) > 0 else "No data"
                    print(f"✅ Column {col}: {len(str(content))} chars")
                else:
                    print(f"❌ Missing column: {col}")
            
            # Cleanup
            os.remove(result_file)
            print(f"🧹 Cleaned up {result_file}")
            
        else:
            print(f"❌ Result file not created: {result_file}")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_sequence()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")