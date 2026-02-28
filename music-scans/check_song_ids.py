#!/usr/bin/env python
"""Check all song files for ID field"""

import json
import os
from pathlib import Path

songs_dir = Path(__file__).parent / "songs"

print("\nChecking all song files for ID field:\n")

for song_file in sorted(songs_dir.glob("*.json")):
    try:
        with open(song_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            song_id = data.get('id')
            song_name = data.get('name', 'Unknown')
            if song_id:
                print(f"✓ {song_file.name}")
                print(f"  ID: {song_id[:8]}...")
                print(f"  Name: {song_name}")
            else:
                print(f"✗ {song_file.name} - MISSING ID FIELD")
                print(f"  Name: {song_name}")
    except Exception as e:
        print(f"✗ {song_file.name} - ERROR: {e}")
    print()
