#!/usr/bin/env python3
"""
Test script to verify job history reconstruction from filesystem
"""
import os
import re
import pandas as pd
from pathlib import Path

def test_job_reconstruction():
    """Test that job history can be reconstructed from filesystem"""
    
    print("Testing job history reconstruction...")
    
    uploads_path = Path("uploads")
    if not uploads_path.exists():
        print("❌ uploads directory doesn't exist")
        return
    
    # Get all UUID-like files (job files)
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(csv|xlsx|xls)$')
    
    job_files = []
    for file_path in uploads_path.iterdir():
        if file_path.is_file() and uuid_pattern.match(file_path.name):
            job_files.append(file_path)
    
    print(f"Found {len(job_files)} job files")
    
    if len(job_files) == 0:
        print("❌ No job files found to test reconstruction")
        return
    
    # Test reconstruction logic on a few files
    test_count = min(5, len(job_files))
    successful_reconstructions = 0
    
    for i, file_path in enumerate(job_files[:test_count]):
        job_id = file_path.stem
        print(f"\nTesting reconstruction for job {i+1}/{test_count}: {job_id}")
        
        try:
            # Try to read the file
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            total_rows = len(df)
            mode = "single"
            
            # Check if it's a sequence job
            if 'initial_email' in df.columns and 'followup_1' in df.columns:
                mode = "sequence"
            
            print(f"  ✓ Successfully read file: {total_rows} rows, mode: {mode}")
            
            # Check for status file
            status_file = uploads_path / f"{job_id}_status.txt"
            if status_file.exists():
                status_text = status_file.read_text().strip()
                print(f"  ✓ Status file exists: {status_text}")
            else:
                print(f"  ⚠ No status file found")
            
            # Check for result file
            result_file_xlsx = uploads_path / f"result_{job_id}.xlsx"
            result_file_csv = uploads_path / f"result_{job_id}.csv"
            
            if result_file_xlsx.exists():
                print(f"  ✓ Result file exists: {result_file_xlsx.name}")
            elif result_file_csv.exists():
                print(f"  ✓ Result file exists: {result_file_csv.name}")
            else:
                print(f"  ⚠ No result file found")
            
            successful_reconstructions += 1
            
        except Exception as e:
            print(f"  ❌ Failed to reconstruct job {job_id}: {e}")
    
    print(f"\n✅ Successfully reconstructed {successful_reconstructions}/{test_count} jobs")
    print(f"Total jobs available for reconstruction: {len(job_files)}")

if __name__ == "__main__":
    # Change to the project directory
    os.chdir("C:/Users/stuar/Desktop/Projects/scalable_email_generator_fixed")
    test_job_reconstruction()