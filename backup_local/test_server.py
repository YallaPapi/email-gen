#!/usr/bin/env python3
"""Quick test to verify the server works"""

import sys
import os
sys.path.insert(0, 'backend')

from pathlib import Path

# Test the path logic
docker_path = Path("/app/frontend/index.html")
local_path = Path("frontend/index.html")

print(f"Docker path exists: {docker_path.exists()}")
print(f"Local path exists: {local_path.exists()}")

if local_path.exists():
    print(f"✅ Frontend found locally at: {local_path}")
    print(f"File size: {local_path.stat().st_size} bytes")
else:
    print("❌ Frontend not found!")