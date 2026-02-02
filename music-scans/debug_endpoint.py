#!/usr/bin/env python3
import sys
import json

# Read lessons.json directly
try:
    with open(r"g:\My Drive\ContentTools\music-scans\lessons.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"File contains: {data}")
        print(f"Length: {len(data)}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

# Now test the API
try:
    import requests
    response = requests.get("http://localhost:5000/api/lessons")
    print(f"API Response status: {response.status_code}")
    print(f"API Response text: {response.text}")
    print(f"API Response JSON: {response.json()}")
except Exception as e:
    print(f"API Error: {e}")
    import traceback
    traceback.print_exc()
