#!/usr/bin/env python3
import sys
sys.path.insert(0, r"g:\My Drive\ContentTools\music-scans")

from app import app, get_lessons, LESSONS_FILE
import json

print(f"LESSONS_FILE: {LESSONS_FILE}")
print(f"LESSONS_FILE exists: {LESSONS_FILE.exists()}")

if LESSONS_FILE.exists():
    content = LESSONS_FILE.read_text(encoding="utf-8").strip()
    print(f"File content length: {len(content)}")
    if content:
        data = json.loads(content)
        print(f"File contains {len(data)} lessons: {data}")

print("\n--- Now test the endpoint ---\n")

# Create a test client
with app.test_client() as client:
    response = client.get('/api/lessons')
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.get_json()}")
