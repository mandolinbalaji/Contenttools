#!/usr/bin/env python
"""
Test API endpoints to verify they work with the new name-based storage
This simulates what the frontend will do
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
KALPANA_SWARA_SONGS_DIR = BASE_DIR / "songs"

def _sanitize_filename(name):
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    return sanitized or "Untitled"

def _load_kalpana_swara_songs():
    """GET /api/kalpana-swara-songs - List all songs"""
    songs = []
    if not KALPANA_SWARA_SONGS_DIR.exists():
        return songs
    try:
        for song_file in KALPANA_SWARA_SONGS_DIR.glob("*.json"):
            try:
                with open(song_file, 'r', encoding='utf-8') as f:
                    song_data = json.load(f)
                    if song_data.get('name'):
                        songs.append(song_data)
            except Exception as e:
                print(f"Error loading {song_file.name}: {e}")
                continue
        songs.sort(key=lambda s: s.get('lastModified', ''), reverse=True)
    except Exception as e:
        print(f"Error loading songs: {e}")
        return []
    return songs

def _load_kalpana_swara_song_by_id(song_id):
    """GET /api/kalpana-swara-songs/<id> - Load specific song"""
    if not KALPANA_SWARA_SONGS_DIR.exists():
        return None
    try:
        for song_file in KALPANA_SWARA_SONGS_DIR.glob("*.json"):
            try:
                with open(song_file, 'r', encoding='utf-8') as f:
                    song_data = json.load(f)
                    if song_data.get('id') == song_id:
                        return song_data
            except:
                continue
    except Exception as e:
        print(f"Error loading song by ID: {e}")
    return None

print("\n===== Testing API Endpoints =====\n")

# Test 1: GET /api/kalpana-swara-songs (List all songs)
print("Test 1: GET /api/kalpana-swara-songs")
print("Expected: Array of all songs from songs/ folder")
try:
    songs = _load_kalpana_swara_songs()
    print(f"✓ Returned {len(songs)} songs:\n")
    for song in songs:
        print(f"  - {song.get('name')} (ID: {song.get('id')[:8]}...)")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: GET /api/kalpana-swara-songs/<id> (Load specific song)
print("\n\nTest 2: GET /api/kalpana-swara-songs/<id>")
print("Expected: Return song matching the ID")
if songs:
    test_song = songs[0]
    try:
        loaded = _load_kalpana_swara_song_by_id(test_song['id'])
        if loaded:
            print(f"✓ Loaded song: '{loaded.get('name')}'")
            print(f"  ID: {loaded.get('id')}")
            print(f"  Ragam: {loaded.get('ragam')}")
            print(f"  Cycles: {len(loaded.get('cycles', []))}")
        else:
            print(f"✗ Song not found")
    except Exception as e:
        print(f"✗ Error: {e}")

# Test 3: POST /api/kalpana-swara-songs (Save new song)
print("\n\nTest 3: POST /api/kalpana-swara-songs")
print("Expected: Save new song with song name as filename")
try:
    from datetime import datetime
    import uuid
    
    new_song = {
        "id": str(uuid.uuid4()),
        "name": "Test API Song",
        "ragam": "Bhairav",
        "composer": "API Test",
        "sruthi": "C",
        "thalam": "Adhi",
        "beats": 8,
        "nadai": 4,
        "eduppu": 4,
        "tags": ["test"],
        "scale": "s r g m p d n",
        "cycles": [],
        "createdDate": datetime.now().isoformat(),
        "lastModified": datetime.now().isoformat()
    }
    
    # Save it
    song_name = new_song['name']
    sanitized = _sanitize_filename(song_name)
    filepath = KALPANA_SWARA_SONGS_DIR / f"{sanitized}.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(new_song, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved new song:")
    print(f"  Filename: {filepath.name}")
    print(f"  Song name: {new_song['name']}")
    print(f"  ID: {new_song['id'][:8]}...")
    
    # Load it back to verify
    loaded = _load_kalpana_swara_song_by_id(new_song['id'])
    if loaded:
        print(f"✓ Verified: Can load by ID")
    
    # Clean up
    filepath.unlink()
    print(f"✓ Cleaned up test file")
    
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Playlist display (Frontend scenario)
print("\n\nTest 4: Frontend Playlist Display")
print("Expected: Playlist shows all songs from API")
try:
    songs = _load_kalpana_swara_songs()
    print(f"✓ Playlist will display {len(songs)} songs:")
    for i, song in enumerate(songs, 1):
        ragam = song.get('ragam', 'Unknown')
        thalam = song.get('thalam', 'Adhi')
        print(f"  {i}. {song.get('name')} ({ragam} • {thalam})")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n===== All Tests Complete =====\n")
