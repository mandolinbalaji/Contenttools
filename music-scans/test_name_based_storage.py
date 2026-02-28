#!/usr/bin/env python
"""Test the updated song storage to verify name-based filenames and proper loading"""

import json
import uuid
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.absolute()
KALPANA_SWARA_SONGS_DIR = BASE_DIR / "songs"

def _sanitize_filename(name):
    """Sanitize song name to create a valid filename"""
    import re
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    return sanitized or "Untitled"

print("\n===== Testing Name-Based Song File Storage =====\n")

# Test 1: List current songs in songs folder
print("Test 1: Listing all JSON files in songs/ folder")
try:
    song_files = list(KALPANA_SWARA_SONGS_DIR.glob("*.json"))
    print(f"✓ Found {len(song_files)} JSON files:")
    for song_file in sorted(song_files):
        print(f"  - {song_file.name}", end="")
        try:
            with open(song_file, 'r', encoding='utf-8') as f:
                song_data = json.load(f)
                song_name = song_data.get('name', '(no name)')
                print(f" -> Song: '{song_name}'")
        except:
            print(" (invalid JSON)")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 2: Test filename sanitization
print("\nTest 2: Testing filename sanitization")
test_names = [
    "Makalarava Vicharamu",
    "Sri! Maha Ganapathi (Gowlai)",
    "Test: Song/Name*123",
    "Sujana   Jeevana"
]
for name in test_names:
    sanitized = _sanitize_filename(name)
    print(f"  '{name}' -> '{sanitized}.json'")

# Test 3: Load all songs
print("\nTest 3: Loading all songs from songs/ folder")
try:
    songs = []
    for song_file in KALPANA_SWARA_SONGS_DIR.glob("*.json"):
        try:
            with open(song_file, 'r', encoding='utf-8') as f:
                song_data = json.load(f)
                if song_data.get('name'):
                    songs.append(song_data)
        except Exception as e:
            print(f"  ! Error loading {song_file.name}: {e}")
    
    print(f"✓ Successfully loaded {len(songs)} songs:")
    for song in sorted(songs, key=lambda s: s.get('name', '')):
        print(f"  - {song.get('name')} (ID: {song.get('id')[:8]}...)")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 4: Create new song with proper filename
print("\nTest 4: Creating new song with name-based filename")
try:
    test_song = {
        "id": str(uuid.uuid4()),
        "name": "Test Song Name Based",
        "ragam": "Dheerashankarabharanam",
        "composer": "Test",
        "sruthi": "C",
        "thalam": "Adhi",
        "beats": 8,
        "nadai": 4,
        "eduppu": 4,
        "tags": ["test"],
        "scale": "s r2 g2 m1 p d2 n2",
        "cycles": [],
        "createdDate": datetime.now().isoformat(),
        "lastModified": datetime.now().isoformat()
    }
    
    # Generate filename from song name
    sanitized_name = _sanitize_filename(test_song['name'])
    test_filepath = KALPANA_SWARA_SONGS_DIR / f"{sanitized_name}.json"
    
    with open(test_filepath, 'w', encoding='utf-8') as f:
        json.dump(test_song, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Song saved as: {test_filepath.name}")
    print(f"  Expected: Test_Song_Name_Based.json")
    print(f"  Song ID in file: {test_song['id'][:8]}...")
    
    # Verify we can load it back
    with open(test_filepath, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
        print(f"✓ Verified: loaded song name = '{loaded['name']}'")
    
    # Clean up
    test_filepath.unlink()
    print(f"✓ Test file cleaned up")
except Exception as e:
    print(f"✗ Failed: {e}")

print("\n===== Test Complete =====\n")
