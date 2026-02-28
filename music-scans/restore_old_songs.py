#!/usr/bin/env python
"""Restore .old song files and convert them to proper JSON with name-based filenames"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
KALPANA_SWARA_SONGS_DIR = BASE_DIR / "songs"

def _sanitize_filename(name):
    """Sanitize song name to create a valid filename"""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    return sanitized or "Untitled"

print("\n===== Restoring .old Song Files =====\n")

# Find all .old files
old_files = list(KALPANA_SWARA_SONGS_DIR.glob("*.old"))
print(f"Found {len(old_files)} .old files\n")

restored_count = 0

for old_file in sorted(old_files):
    print(f"Processing: {old_file.name}")
    
    try:
        with open(old_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Determine the song name from the .old filename or from the data
        base_name = old_file.stem  # Remove .old extension
        song_name = data.get('name', base_name)
        
        # Create the new JSON filename
        new_name = _sanitize_filename(song_name)
        new_filepath = KALPANA_SWARA_SONGS_DIR / f"{new_name}.json"
        
        # Check if it already exists
        if new_filepath.exists():
            print(f"  ! {new_filepath.name} already exists, skipping")
            continue
        
        # Save as JSON with new filename
        with open(new_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Restored as: {new_filepath.name}")
        print(f"    Song name: '{song_name}'")
        restored_count += 1
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Failed to parse JSON: {e}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print(f"\n===== Restoration Complete =====")
print(f"Restored: {restored_count} songs\n")

# List final state
print(f"Songs now available in folder:")
final_songs = []
for song_file in sorted(KALPANA_SWARA_SONGS_DIR.glob("*.json")):
    try:
        with open(song_file, 'r', encoding='utf-8') as f:
            song = json.load(f)
            if isinstance(song, dict) and song.get('name'):
                final_songs.append((song_file.name, song.get('name')))
                print(f"  ✓ {song_file.name}")
    except:
        pass

print(f"\nTotal valid songs: {len(final_songs)}\n")
