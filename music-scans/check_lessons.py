#!/usr/bin/env python3
import json
from pathlib import Path

BASE_DIR = Path(r"g:\My Drive\ContentTools\music-scans")
LESSONS_FILE = BASE_DIR / "lessons.json"

print("=" * 60)
print("LESSONS.JSON FILE CHECK")
print("=" * 60)
print(f"\nBASE_DIR: {BASE_DIR}")
print(f"LESSONS_FILE path: {LESSONS_FILE}")
print(f"File exists: {LESSONS_FILE.exists()}")

if LESSONS_FILE.exists():
    print(f"File size: {LESSONS_FILE.stat().st_size} bytes")
    
    try:
        content = LESSONS_FILE.read_text(encoding="utf-8")
        print(f"Content length: {len(content)} characters")
        print(f"\nFile content (first 500 chars):\n{content[:500]}")
        
        data = json.loads(content)
        print(f"\n✓ Valid JSON!")
        print(f"Number of lessons: {len(data)}")
        
        if data:
            print(f"\nLessons found:")
            for lesson in data:
                print(f"  - {lesson.get('name', 'Unknown')}")
                print(f"    ID: {lesson.get('id', 'No ID')}")
                print(f"    Notes: {lesson.get('notes', 'No notes')[:50]}...")
                print(f"    Thala: {lesson.get('thala', 'No thala')}")
                print(f"    Timestamp: {lesson.get('timestamp', 'No timestamp')}")
        else:
            print("\n✗ Lessons array is empty!")
            
    except json.JSONDecodeError as e:
        print(f"\n✗ Invalid JSON: {e}")
    except Exception as e:
        print(f"\n✗ Error reading file: {e}")
else:
    print(f"\n✗ lessons.json NOT FOUND!")

print("\n" + "=" * 60)
