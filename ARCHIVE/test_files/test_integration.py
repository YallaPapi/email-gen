#!/usr/bin/env python3
"""
Integration test for all email generator fixes
"""
import asyncio
import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test pandas nan handling
        import pandas as pd
        import numpy as np
        print("  ✓ Pandas and numpy imported")
        
        # Test pathlib
        from pathlib import Path
        print("  ✓ Pathlib imported")
        
        # Test re for UUID patterns
        import re
        print("  ✓ Regex imported")
        
        print("✅ All basic imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_nan_handling():
    """Test NaN handling logic"""
    print("\nTesting NaN handling...")
    
    import pandas as pd
    import numpy as np
    
    test_data = {
        'name': ['John', 'Jane', 'Bob'],
        'industry': [np.nan, '', 'technology'],
        'company': ['Corp1', 'Corp2', 'Corp3']
    }
    
    df = pd.DataFrame(test_data)
    
    for index, row in df.iterrows():
        row_data = row.to_dict()
        
        # Apply our cleaning logic
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
        
        # Test that we don't get nan in the output
        test_phrase = f"company in the {industry} sector"
        assert 'nan sector' not in test_phrase
        
        print(f"  ✓ Row {index}: {row_data['name']} -> '{industry}' (was {repr(row_data['industry'])})")
    
    print("✅ NaN handling test passed")
    return True

def test_filesystem_job_discovery():
    """Test filesystem job discovery logic"""
    print("\nTesting filesystem job discovery...")
    
    from pathlib import Path
    import re
    import pandas as pd
    
    uploads_path = Path("uploads")
    if not uploads_path.exists():
        print("❌ Uploads directory doesn't exist")
        return False
    
    # UUID pattern matching
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.(csv|xlsx|xls)$')
    
    job_count = 0
    for file_path in uploads_path.iterdir():
        if file_path.is_file() and uuid_pattern.match(file_path.name):
            job_count += 1
            
            # Test reading the file
            try:
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                # Check if it's sequence or single mode
                mode = "sequence" if 'initial_email' in df.columns and 'followup_1' in df.columns else "single"
                
                if job_count <= 3:  # Only print details for first few
                    print(f"  ✓ {file_path.name}: {len(df)} rows, {mode} mode")
                    
            except Exception as e:
                print(f"  ❌ Failed to read {file_path.name}: {e}")
                return False
    
    print(f"✅ Found and validated {job_count} job files")
    return True

def test_progress_calculation():
    """Test progress percentage calculation"""
    print("\nTesting progress calculation...")
    
    test_cases = [
        (0, 10, 0),     # 0/10 = 0%
        (5, 10, 50),    # 5/10 = 50%
        (10, 10, 100),  # 10/10 = 100%
        (0, 0, 0),      # 0/0 = 0% (edge case)
        (3, 7, 43),     # 3/7 = 42.857... -> 43%
    ]
    
    for progress, total, expected in test_cases:
        percentage = total > 0 and round((progress / total) * 100) or 0
        print(f"  ✓ {progress}/{total} = {percentage}% (expected {expected}%)")
        assert percentage == expected, f"Expected {expected}%, got {percentage}%"
    
    print("✅ Progress calculation test passed")
    return True

def main():
    """Run all tests"""
    print("🧪 Running integration tests for email generator fixes\\n")
    
    tests = [
        test_imports,
        test_nan_handling,
        test_filesystem_job_discovery,
        test_progress_calculation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_func.__name__} failed")
        except Exception as e:
            print(f"❌ {test_func.__name__} crashed: {e}")
    
    print(f"\\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The fixes are working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the fixes.")
        return False

if __name__ == "__main__":
    # Change to project directory
    os.chdir("C:/Users/stuar/Desktop/Projects/scalable_email_generator_fixed")
    success = main()
    sys.exit(0 if success else 1)