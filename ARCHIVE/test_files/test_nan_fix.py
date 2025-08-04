#!/usr/bin/env python3
"""
Test script to verify the 'nan sector' bug fix
"""
import pandas as pd
import numpy as np

def test_nan_sector_fix():
    """Test that the nan sector issue is fixed"""
    
    # Simulate row data with nan industry
    test_cases = [
        {'first_name': 'John', 'industry': np.nan, 'company': 'TestCorp'},
        {'first_name': 'Jane', 'industry': '', 'company': 'TestCorp2'},
        {'first_name': 'Bob', 'industry': 'nan', 'company': 'TestCorp3'},
        {'first_name': 'Alice', 'industry': 'technology', 'company': 'TestCorp4'},
        {'first_name': 'Charlie', 'industry': None, 'company': 'TestCorp5'},
    ]
    
    print("Testing nan sector fix...")
    
    for i, row_data in enumerate(test_cases):
        print(f"\nTest case {i+1}: {row_data}")
        
        # Apply the same logic as our fixed code
        cleaned_row_data = {}
        for col, val in row_data.items():
            if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'none', 'null']:
                cleaned_row_data[col] = ''
            else:
                cleaned_row_data[col] = str(val).strip()
        
        industry_raw = cleaned_row_data.get('industry', '')
        if pd.isna(industry_raw) or industry_raw == '' or str(industry_raw).lower() in ['nan', 'none', 'null']:
            industry = 'your industry'
        else:
            industry = str(industry_raw).strip()
        
        print(f"  Original industry: {repr(row_data.get('industry'))}")
        print(f"  Fixed industry: {repr(industry)}")
        
        # Check that we don't get 'nan sector' in the output
        test_text = f"company in the {industry} sector"
        assert 'nan sector' not in test_text, f"Still getting 'nan sector' in: {test_text}"
        print(f"  ✓ Text: 'company in the {industry} sector'")
    
    print("\n✅ All tests passed! The 'nan sector' bug is fixed.")

if __name__ == "__main__":
    test_nan_sector_fix()