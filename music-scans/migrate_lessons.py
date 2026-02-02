#!/usr/bin/env python3
import json
from pathlib import Path

base_dir = Path('.')
lessons_dir = base_dir / 'lessons'
lessons_file = base_dir / 'lessons.json'

# Load all individual lesson files
lessons = []
if lessons_dir.exists():
    for json_file in lessons_dir.glob('*.json'):
        try:
            data = json.loads(json_file.read_text(encoding='utf-8'))
            lessons.append(data)
            print(f"Migrated: {data.get('name', json_file.stem)}")
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

# Save to single lessons.json
if lessons:
    lessons_file.write_text(json.dumps(lessons, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nSuccessfully migrated {len(lessons)} lessons to lessons.json")
else:
    print("No lessons found to migrate")
