#!/usr/bin/env python3
"""Quick debug script to test if mode parameter is working"""

import requests

# Test sequence mode
files = {'file': ('test_sequence.csv', open('test_sequence.csv', 'rb'))}
data = {'mode': 'sequence'}

response = requests.post('http://localhost:8000/upload', files=files, data=data)
print("Response:", response.json())

job_id = response.json()['job_id']
print(f"Job ID: {job_id}")

# Check if the mode was registered
import time
time.sleep(5)

status_response = requests.get(f'http://localhost:8000/status/{job_id}')
print("Status:", status_response.json())