#!/usr/bin/env python3
"""Quick test script to verify the email generator works locally"""

import asyncio
import sys
import os
sys.path.append('./backend')

from backend.tasks import process_spreadsheet_task

# Test the email generation directly
def test_email_generation():
    print("Testing email generation...")
    
    # Test file
    test_file = "test_prospects.csv"
    job_id = "test-123"
    
    # Run the task synchronously for testing
    result = process_spreadsheet_task(test_file, job_id)
    
    print(f"Result: {result}")
    
    # Check if output file was created
    output_file = f"uploads/result_{job_id}.xlsx"
    if os.path.exists(output_file):
        print(f"✅ Success! Output file created: {output_file}")
    else:
        print("❌ Failed - no output file created")

if __name__ == "__main__":
    test_email_generation()