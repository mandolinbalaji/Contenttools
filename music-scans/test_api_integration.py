#!/usr/bin/env python
"""Test script to verify KalpanaSwaramComposer API integration with songs/ folder"""

import json
import uuid
from pathlib import Path
from datetime import datetime

# Set up paths
BASE_DIR = Path(__file__).parent.absolute()
KALPANA_SWARA_SONGS_DIR = BASE_DIR / "songs"

def test_song_file_operations():
    """Test basic file operations for song storage"""
    print("\n===== Testing Song File Operations =====\n")
    
    # Create test song data
    test_song = {
        "id": str(uuid.uuid4()),
        "name": "Test Song - API Integration",
        "ragam": "Dheerashankarabharanam",
        "composer": "Test Composer",
        "sruthi": "C",
        "thalam": "Adhi Thalam",
        "beats": 8,
        "nadai": 4,
        "eduppu": 4,
        "tags": ["test"],
        "scale": "s r2 g2 m1 p d2 n2",
        "cycles": [{
            "id": str(uuid.uuid4()),
            "phraseText": "s r g p d",
            "phraseDisplay": "s r g p d",
            "noteCount": 5,
            "lyrics": "sa|ri|ga|pa|dha",
            "comments": "Test phrase",
            "expanded": True
        }],
        "createdDate": datetime.now().isoformat(),
        "lastModified": datetime.now().isoformat()
    }
    
    # Test 1: Save song to file
    print(f"Test 1: Saving song '{test_song['name']}' to songs/ folder")
    song_filename = f"{test_song['id']}.json"
    song_filepath = KALPANA_SWARA_SONGS_DIR / song_filename
    
    try:
        with open(song_filepath, 'w', encoding='utf-8') as f:
            json.dump(test_song, f, indent=2, ensure_ascii=False)
        print(f"✓ Song saved to: {song_filepath}")
        print(f"  File size: {song_filepath.stat().st_size} bytes")
    except Exception as e:
        print(f"✗ Failed to save song: {e}")
        return False
    
    # Test 2: Load song from file
    print(f"\nTest 2: Loading song from file")
    try:
        with open(song_filepath, 'r', encoding='utf-8') as f:
            loaded_song = json.load(f)
        print(f"✓ Song loaded successfully")
        print(f"  Song name: {loaded_song['name']}")
        print(f"  ID: {loaded_song['id']}")
        print(f"  Cycles: {len(loaded_song['cycles'])}")
    except Exception as e:
        print(f"✗ Failed to load song: {e}")
        return False
    
    # Test 3: List all songs in folder
    print(f"\nTest 3: Listing all songs in songs/ folder")
    try:
        song_files = list(KALPANA_SWARA_SONGS_DIR.glob("*.json"))
        print(f"✓ Found {len(song_files)} song files")
        for song_file in sorted(song_files):
            try:
                with open(song_file, 'r', encoding='utf-8') as f:
                    song_data = json.load(f)
                    print(f"  - {song_data.get('name', 'Unknown')} ({song_file.name})")
            except:
                print(f"  - (Could not read {song_file.name})")
    except Exception as e:
        print(f"✗ Failed to list songs: {e}")
        return False
    
    # Test 4: Update song
    print(f"\nTest 4: Updating song")
    try:
        loaded_song['name'] = "Updated Test Song - API Integration"
        loaded_song['lastModified'] = datetime.now().isoformat()
        
        with open(song_filepath, 'w', encoding='utf-8') as f:
            json.dump(loaded_song, f, indent=2, ensure_ascii=False)
        print(f"✓ Song updated successfully")
        print(f"  New name: {loaded_song['name']}")
    except Exception as e:
        print(f"✗ Failed to update song: {e}")
        return False
    
    # Test 5: Delete song
    print(f"\nTest 5: Deleting test song")
    try:
        song_filepath.unlink()
        if not song_filepath.exists():
            print(f"✓ Song deleted successfully")
        else:
            print(f"✗ File still exists after deletion")
            return False
    except Exception as e:
        print(f"✗ Failed to delete song: {e}")
        return False
    
    print("\n===== All Tests Passed! =====\n")
    return True

if __name__ == "__main__":
    print("\nKalpanaSwaramComposer API Integration Test")
    print("=" * 50)
    print(f"Songs Directory: {KALPANA_SWARA_SONGS_DIR}")
    print(f"Directory exists: {KALPANA_SWARA_SONGS_DIR.exists()}")
    
    success = test_song_file_operations()
    exit(0 if success else 1)
