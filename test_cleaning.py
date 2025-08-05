#!/usr/bin/env python3

def nuclear_clean_email_test(email_text):
    """TEST VERSION OF NUCLEAR CLEANING"""
    import re
    
    text = str(email_text).strip()
    
    # STEP 1: ELIMINATE ALL HIGH UNICODE (EMOJIS)
    # Remove ALL characters above basic ASCII range that could be emojis
    # More comprehensive emoji removal - covers most emoji ranges
    text = ''.join(char for char in text if ord(char) < 127 or char in ' \n\t\r')
    
    return text

# Test the function with actual failing content
test_cases = [
    "Hey Sarah,\n\nI hope you're not too caught up in a riveting game of competitive ping pong to reply! 😄 If I don't hear back, I'll assume you've been recruited by a hospital for your amazing reflexes.",
    "Hey Dr. Chen,\n\nI guess you must be perfecting your world-renowned interpretive dance routine instead of replying to my emails.",
    "Hey Jennifer,\n\nI hope you're not trapped under a pile of paperwork or lost in a labyrinth of spreadsheets over at CareTech Innovations! 😄"
]

for i, test in enumerate(test_cases):
    print(f"TEST CASE {i+1}:")
    print("BEFORE:", repr(test))
    cleaned = nuclear_clean_email_test(test)
    print("AFTER:", repr(cleaned))
    print("Contains emoji?", any(ord(char) > 127 for char in cleaned))
    print()