#!/usr/bin/env python
"""Migrate songs folder to use name-based filenames"""

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

print("\n===== Migrating Songs to Name-Based Filenames =====\n")

# Find all JSON files
json_files = list(KALPANA_SWARA_SONGS_DIR.glob("*.json"))
print(f"Found {len(json_files)} JSON files in songs/ folder\n")

renamed_count = 0
deleted_count = 0

for json_file in sorted(json_files):
    print(f"Processing: {json_file.name}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if it's an array (old format)
        if isinstance(data, list):
            print(f"  ! This is an array file (old format) with {len(data)} songs")
            print(f"  → Saving as individual files...")
            
            for i, song in enumerate(data):
                if song.get('name'):
                    new_name = _sanitize_filename(song['name'])
                    new_filepath = KALPANA_SWARA_SONGS_DIR / f"{new_name}.json"
                    
                    with open(new_filepath, 'w', encoding='utf-8') as f:
                        json.dump(song, f, indent=2, ensure_ascii=False)
                    print(f"    ✓ Saved: {new_filepath.name} (song #{i+1})")
                    renamed_count += 1
            
            # Delete the old array file
            json_file.unlink()
            print(f"  ✓ Deleted old array file: {json_file.name}")
            deleted_count += 1
        
        # Check if it's a single song object
        elif isinstance(data, dict) and data.get('name'):
            song_name = data['name']
            new_name = _sanitize_filename(song_name)
            expected_filename = f"{new_name}.json"
            
            # Only rename if filename doesn't match
            if json_file.name != expected_filename:
                new_filepath = KALPANA_SWARA_SONGS_DIR / expected_filename
                
                # Check if target already exists
                if new_filepath.exists():
                    print(f"  ! Target {expected_filename} already exists, keeping both")
                else:
                    json_file.rename(new_filepath)
                    print(f"  ✓ Renamed: {json_file.name} → {expected_filename}")
                    renamed_count += 1
            else:
                print(f"  ✓ Already correct: {json_file.name}")
        
        # Empty or invalid song
        elif not data.get('name'):
            print(f"  ! Invalid: No song name found, deleting")
            json_file.unlink()
            deleted_count += 1
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON: {e}, skipping")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print(f"\n===== Migration Complete =====")
print(f"Renamed: {renamed_count}")
print(f"Deleted: {deleted_count}")

# List final state
print(f"\nFinal songs in folder:")
final_songs = []
for song_file in sorted(KALPANA_SWARA_SONGS_DIR.glob("*.json")):
    try:
        with open(song_file, 'r', encoding='utf-8') as f:
            song = json.load(f)
            if isinstance(song, dict) and song.get('name'):
                final_songs.append((song_file.name, song.get('name')))
                print(f"  ✓ {song_file.name} → '{song.get('name')}'")
    except:
        pass

print(f"\nTotal valid songs: {len(final_songs)}\n")
