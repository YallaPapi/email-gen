#!/usr/bin/env python3
"""
Excel File Analyzer Script
Analyzes Excel files to show row count, columns, and sample data.
"""

import pandas as pd
import sys
import os

def analyze_excel_file(file_path):
    """
    Analyze an Excel file and display key information.
    
    Args:
        file_path (str): Path to the Excel file
    """
    print(f"Analyzing Excel file: {file_path}")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist: {file_path}")
        return False
    
    try:
        # Read the Excel file
        print("Reading Excel file...")
        df = pd.read_excel(file_path)
        
        # 1. Row count
        row_count = len(df)
        print(f"\n1. NUMBER OF ROWS: {row_count}")
        
        # 2. Columns present
        columns = df.columns.tolist()
        print(f"\n2. COLUMNS PRESENT ({len(columns)} total):")
        for i, col in enumerate(columns, 1):
            print(f"   {i}. {col}")
        
        # 3. Show first few rows
        print(f"\n3. FIRST FEW ROWS OF DATA:")
        print("-" * 60)
        
        if row_count > 0:
            # Show first 5 rows (or all rows if less than 5)
            sample_rows = min(5, row_count)
            print(f"Showing first {sample_rows} rows:")
            print()
            
            # Display with better formatting
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 100)
            
            print(df.head(sample_rows).to_string(index=True))
            
            if row_count > 5:
                print(f"\n... and {row_count - 5} more rows")
        else:
            print("No data rows found in the file.")
        
        # Additional info
        print(f"\n4. ADDITIONAL INFORMATION:")
        print(f"   - File size: {os.path.getsize(file_path)} bytes")
        print(f"   - Data types:")
        for col, dtype in df.dtypes.items():
            print(f"     {col}: {dtype}")
        
        # Check for empty cells
        null_counts = df.isnull().sum()
        if null_counts.any():
            print(f"\n5. EMPTY/NULL CELLS:")
            for col, null_count in null_counts.items():
                if null_count > 0:
                    print(f"   {col}: {null_count} empty cells")
        
        return True
        
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        return False
    except PermissionError:
        print(f"ERROR: Permission denied accessing file: {file_path}")
        return False
    except pd.errors.EmptyDataError:
        print("ERROR: The Excel file is empty or corrupted.")
        return False
    except Exception as e:
        print(f"ERROR: Failed to read Excel file: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

def main():
    """Main function to run the Excel analyzer."""
    # Default file path
    default_file = r"C:\Users\stuar\Desktop\Projects\scalable_email_generator_fixed\uploads\result_47ef53d4-3301-4d0b-bcf0-8493c4be0582.xlsx"
    
    # Check if a file path was provided as command line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file
    
    print("Excel File Analyzer")
    print("==================")
    
    success = analyze_excel_file(file_path)
    
    if success:
        print("\nAnalysis completed successfully!")
    else:
        print("\nAnalysis failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()