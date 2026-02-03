#!/usr/bin/env python3
import requests
import json
import time

time.sleep(0.5)

try:
    # Test lessons endpoint
    r1 = requests.get('http://127.0.0.1:5000/api/lessons')
    print(f"✓ Lessons endpoint: {r1.status_code}")
    data1 = r1.json()
    print(f"  Returns: {type(data1).__name__} with {len(data1)} items")
    if isinstance(data1, list) and len(data1) > 0:
        print(f"  First item keys: {list(data1[0].keys())[:3]}")
    
    # Test thala-beats endpoint  
    r2 = requests.get('http://127.0.0.1:5000/api/thala-beats')
    print(f"✓ Thala-beats endpoint: {r2.status_code}")
    data2 = r2.json()
    print(f"  Returns: {type(data2).__name__} with {len(data2)} items")
    print(f"  Sample: {dict(list(data2.items())[:2])}")
except Exception as e:
    print(f"✗ Error: {e}")
