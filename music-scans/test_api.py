#!/usr/bin/env python3
"""
Test the Flask API endpoints directly
"""
import json
from pathlib import Path

BASE_DIR = Path(r"g:\My Drive\ContentTools\music-scans")
LESSONS_FILE = BASE_DIR / "lessons.json"

def _load_lessons():
    """Load all lessons from lessons.json"""
    print(f"DEBUG: Loading lessons from: {LESSONS_FILE}")
    print(f"DEBUG: File exists: {LESSONS_FILE.exists()}")
    
    if not LESSONS_FILE.exists():
        print("DEBUG: lessons.json does not exist, returning empty list")
        return []
    try:
        content = LESSONS_FILE.read_text(encoding="utf-8").strip()
        print(f"DEBUG: File content length: {len(content)} characters")
        if not content:
            print("DEBUG: File is empty")
            return []
        data = json.loads(content)
        print(f"DEBUG: Loaded {len(data)} lessons")
        print(f"DEBUG: Lessons data: {data}")
        return data
    except Exception as e:
        print(f"ERROR loading lessons: {e}")
        return []

print("=" * 70)
print("TESTING /api/lessons ENDPOINT")
print("=" * 70)

print("\n=== API /api/lessons GET called ===")
lessons = _load_lessons()
print(f"DEBUG: Returning {len(lessons)} lessons")

if lessons:
    sorted_lessons = sorted(lessons, key=lambda x: x.get("name", ""))
    print(f"\n✓ SUCCESS! Would return {len(sorted_lessons)} lessons:")
    for lesson in sorted_lessons:
        print(f"\n  Lesson: {lesson.get('name', 'Unknown')}")
        print(f"    ID: {lesson.get('id')}")
        print(f"    Notes: {lesson.get('notes', '')[:60]}...")
        print(f"    Thala: {lesson.get('thala')}")
        print(f"    Jathi: {lesson.get('jathi')}")
        print(f"    Nadai: {lesson.get('nadai')}")
        print(f"    Sruthi: {lesson.get('sruthi')}")
        print(f"    Timestamp: {lesson.get('timestamp')}")
else:
    print("\n✗ FAILED! No lessons returned")

print("\n" + "=" * 70)
