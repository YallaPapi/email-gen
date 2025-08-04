#!/usr/bin/env python3

"""
Test what's actually running in production by calling the exact function
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_actual_imports():
    """Test what's actually imported and used"""
    
    print("=== TESTING ACTUAL PRODUCTION SETUP ===")
    
    # Check Python path and working directory
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path includes: {[p for p in sys.path if 'scalable_email' in p]}")
    
    # Try to import without the problematic OpenAI import
    print("\n=== TESTING WITHOUT OPENAI IMPORT ===")
    
    # Read the tasks.py file and check if there might be import issues
    try:
        with open('tasks.py', 'r') as f:
            content = f.read()
        
        print(f"Tasks.py file size: {len(content)} characters")
        
        # Check if we're using the old OpenAI API
        if "from openai import OpenAI" in content:
            print("✓ File uses new OpenAI API (v1.x)")
        elif "import openai" in content:
            print("✓ File uses old OpenAI API (v0.x)")
        else:
            print("✗ No OpenAI import found")
        
        # Check for the specific prompt phrases
        target_phrase = "if you're open to a chat, let me know - if not, all good"
        wrong_phrase = "totally cool"
        alt_wrong_phrase = "I'd love to chat"
        
        if target_phrase in content:
            print(f"✓ Found correct phrase: '{target_phrase}'")
        else:
            print(f"✗ Missing correct phrase: '{target_phrase}'")
            
        if wrong_phrase in content:
            print(f"✗ Found wrong phrase: '{wrong_phrase}'")
        else:
            print(f"✓ No wrong phrase: '{wrong_phrase}'")
            
        if alt_wrong_phrase in content:
            print(f"✗ Found alternative wrong phrase: '{alt_wrong_phrase}'")
        else:
            print(f"✓ No alternative wrong phrase: '{alt_wrong_phrase}'")
            
    except Exception as e:
        print(f"✗ Error reading tasks.py: {e}")
    
    print("\n=== CHECKING ENVIRONMENT VARIABLES ===")
    
    # Check if there are any environment variables that might affect behavior
    env_vars = ['OPENAI_API_KEY', 'PYTHONPATH', 'CELERY_BROKER_URL']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Don't print the actual key value
            if 'KEY' in var:
                print(f"{var}: <present, length {len(value)}>")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: <not set>")
    
    print("\n=== CHECKING FOR ALTERNATE TASK FILES ===")
    
    # Check if there might be a different tasks file being used
    task_files = []
    for file in os.listdir('.'):
        if file.startswith('task') and file.endswith('.py'):
            task_files.append(file)
    
    print(f"Found task files: {task_files}")
    
    # Check main.py imports
    try:
        with open('main.py', 'r') as f:
            main_content = f.read()
        
        print(f"\nMain.py imports:")
        import_lines = [line.strip() for line in main_content.split('\n') if 'import' in line and 'tasks' in line]
        for line in import_lines:
            print(f"  {line}")
            
    except Exception as e:
        print(f"✗ Error reading main.py: {e}")
    
    print("\n=== RECOMMENDATIONS ===")
    print("Based on the analysis, the issue appears to be:")
    print("1. The tasks.py file has the correct prompts")
    print("2. But the output shows different text ('totally cool' instead of 'all good')")
    print("3. This suggests either:")
    print("   a) OpenAI API version incompatibility")
    print("   b) Cached/compiled code being used")
    print("   c) Different environment running the actual code")
    print("   d) Model behavior variation despite correct prompts")

if __name__ == "__main__":
    test_actual_imports()