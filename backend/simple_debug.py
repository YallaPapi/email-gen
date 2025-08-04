#!/usr/bin/env python3

"""
Simple debug script to check function definitions without importing OpenAI
"""

import ast
import inspect
import os

def analyze_tasks_file():
    """Read and analyze the tasks.py file directly"""
    
    print("=== ANALYZING CURRENT TASKS.PY FILE ===")
    
    if not os.path.exists('tasks.py'):
        print("✗ tasks.py not found")
        return
    
    # Read the file content
    with open('tasks.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"✓ File size: {len(content)} characters")
    
    # Parse with AST to find functions
    try:
        tree = ast.parse(content)
        functions = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions[node.name] = {
                    'line_start': node.lineno,
                    'args': [arg.arg for arg in node.args.args]
                }
        
        print(f"✓ Found {len(functions)} functions")
        
        # Check for our target functions
        if 'process_single_email_direct' in functions:
            func_info = functions['process_single_email_direct']
            print(f"✓ process_single_email_direct found at line {func_info['line_start']}")
            print(f"  Arguments: {func_info['args']}")
        else:
            print("✗ process_single_email_direct NOT found")
        
        if 'process_single_email' in functions:
            func_info = functions['process_single_email']
            print(f"✓ process_single_email found at line {func_info['line_start']}")
            print(f"  Arguments: {func_info['args']}")
        else:
            print("✗ process_single_email NOT found")
            
    except SyntaxError as e:
        print(f"✗ Syntax error in tasks.py: {e}")
        return
    
    # Check for key phrases in the content
    print("\n=== CHECKING PROMPT CONTENT ===")
    
    correct_phrase = "if you're open to a chat, let me know - if not, all good"
    incorrect_phrase = "I'd love to chat"
    
    correct_count = content.count(correct_phrase)
    incorrect_count = content.count(incorrect_phrase)
    
    print(f"✓ Correct phrase '{correct_phrase}' appears {correct_count} times")
    print(f"✓ Incorrect phrase '{incorrect_phrase}' appears {incorrect_count} times")
    
    if correct_count > 0:
        print("✓ File contains correct ending phrase")
    else:
        print("✗ File does NOT contain correct ending phrase")
        
    if incorrect_count > 0:
        print("✗ File contains incorrect phrase - this might be the problem!")
    else:
        print("✓ File does not contain incorrect phrase")
    
    # Find line numbers where phrases appear
    lines = content.split('\n')
    print("\n=== PHRASE LOCATIONS ===")
    
    for i, line in enumerate(lines, 1):
        if correct_phrase in line:
            print(f"  Line {i}: {line.strip()}")
        if incorrect_phrase in line:
            print(f"  ✗ PROBLEM Line {i}: {line.strip()}")
    
    # Check the specific process_single_email_direct function
    print("\n=== CHECKING PROCESS_SINGLE_EMAIL_DIRECT FUNCTION ===")
    
    try:
        # Find the function in the content
        func_start = content.find('def process_single_email_direct(')
        if func_start != -1:
            # Find the next function or end of file
            next_func = content.find('\ndef ', func_start + 1)
            next_decorator = content.find('\n@', func_start + 1)
            
            func_end = len(content)
            if next_func != -1:
                func_end = min(func_end, next_func)
            if next_decorator != -1:
                func_end = min(func_end, next_decorator)
            
            func_content = content[func_start:func_end]
            
            print(f"✓ Function content length: {len(func_content)} characters")
            
            if correct_phrase in func_content:
                print("✓ Function contains correct ending phrase")
            else:
                print("✗ Function does NOT contain correct ending phrase")
                
            if incorrect_phrase in func_content:
                print("✗ Function contains incorrect phrase!")
            else:
                print("✓ Function does not contain incorrect phrase")
                
            # Show the prompt part
            prompt_start = func_content.find('user_prompt = f"""')
            if prompt_start != -1:
                prompt_end = func_content.find('"""', prompt_start + 18)
                if prompt_end != -1:
                    prompt_content = func_content[prompt_start:prompt_end + 3]
                    print(f"\n=== USER PROMPT CONTENT ===")
                    print(prompt_content)
            
        else:
            print("✗ process_single_email_direct function not found in content")
            
    except Exception as e:
        print(f"✗ Error analyzing function: {e}")

def check_other_task_files():
    """Check if there are other task files that might be interfering"""
    
    print("\n=== CHECKING OTHER TASK FILES ===")
    
    task_files = [
        'tasks_original.py',
        'tasks_broken.py'
    ]
    
    for task_file in task_files:
        if os.path.exists(task_file):
            print(f"\n--- Checking {task_file} ---")
            
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if this file has the wrong phrase
            incorrect_phrase = "I'd love to chat"
            if incorrect_phrase in content:
                print(f"✗ {task_file} contains incorrect phrase!")
                
                # Find line numbers
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if incorrect_phrase in line:
                        print(f"  ✗ Line {i}: {line.strip()}")
            else:
                print(f"✓ {task_file} does not contain incorrect phrase")

if __name__ == "__main__":
    os.chdir('C:/Users/stuar/Desktop/Projects/scalable_email_generator_fixed/backend')
    analyze_tasks_file()
    check_other_task_files()