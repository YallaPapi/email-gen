#!/usr/bin/env python3

import re

def nuclear_clean_email(email_text):
    """NUCLEAR CLEANING - REMOVE EVERYTHING UNWANTED WITH REGEX"""
    
    # Step 1: Remove subject lines completely (any line starting with subject)
    email_text = re.sub(r'^Subject:.*$', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    email_text = re.sub(r'^subject:.*$', '', email_text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Step 2: Split into lines and find greeting start
    lines = email_text.split('\n')
    start_index = 0
    
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean.startswith(('Hey ', 'Hi ', 'Hello ')):
            start_index = i
            break
    
    # Take only from greeting onwards
    lines = lines[start_index:]
    
    # Step 3: Remove signature patterns aggressively
    signature_patterns = [
        r'^\s*Cheers!?\s*$',
        r'^\s*Best!?\s*$', 
        r'^\s*Thanks!?\s*$',
        r'^\s*Regards?\s*$',
        r'^\s*Sincerely\s*$',
        r'^\s*\[Your Name\]\s*$',
        r'^\s*\[.*\]\s*$',
        r'^\s*Yours truly\s*$',
        r'^\s*Warm regards\s*$'
    ]
    
    # Filter out signature lines
    filtered_lines = []
    for line in lines:
        is_signature = False
        for pattern in signature_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                is_signature = True
                break
        if not is_signature:
            filtered_lines.append(line)
    
    # Step 4: Remove trailing empty lines and signature remnants
    while filtered_lines and (not filtered_lines[-1].strip() or 
                              filtered_lines[-1].strip().lower() in ['cheers', 'best', 'thanks', 'regards']):
        filtered_lines.pop()
    
    # Step 5: Join and aggressive final cleanup
    result = '\n'.join(filtered_lines)
    
    # Nuclear regex cleanup - remove any remaining unwanted patterns
    result = re.sub(r'Subject:.*?\n', '', result, flags=re.IGNORECASE)
    result = re.sub(r'Cheers!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Best!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Thanks!?[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'Regards[,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'\[Your Name\][,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    result = re.sub(r'\[.*\][,\s]*$', '', result, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up multiple newlines and trailing whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    result = result.strip()
    
    return result

# Test cases that simulate problematic AI outputs
test_cases = [
    """Subject: AI Automation for TechCorp

Hey Mike,

I work with AI automation and help companies like TechCorp streamline their operations. 

Cheers!

[Your Name]""",
    
    """Subject: Quick question about automation

Hi Sarah,

Hope you're doing well. I specialize in AI automation and thought there might be ways to help your business.

Best regards,
John""",
    
    """Hey David,

I work with AI automation and noticed your company could benefit from our services.

Thanks!""",
    
    """Subject: AI Solutions

Hello there,

Quick note about AI automation opportunities.

Best!

[Your Name]"""
]

print("=== TESTING NUCLEAR CLEANING FUNCTION ===\n")

for i, test_input in enumerate(test_cases, 1):
    print(f"--- TEST CASE {i} ---")
    print("INPUT:")
    print(repr(test_input))
    print("\nINPUT (formatted):")
    print(test_input)
    
    cleaned = nuclear_clean_email(test_input)
    
    print("\nOUTPUT:")
    print(repr(cleaned))
    print("\nOUTPUT (formatted):")
    print(cleaned)
    
    # Check for forbidden content
    forbidden_found = []
    lower_cleaned = cleaned.lower()
    
    if 'subject:' in lower_cleaned:
        forbidden_found.append('SUBJECT LINES')
    if any(word in lower_cleaned for word in ['cheers', 'best,', 'best!', 'regards', 'thanks!', '[your name]']):
        forbidden_found.append('SIGNATURES')
    
    print("\nVALIDATION:")
    if forbidden_found:
        print(f"❌ STILL FOUND: {forbidden_found}")
    else:
        print("✅ NO FORBIDDEN CONTENT DETECTED")
    
    print("\n" + "="*50 + "\n")