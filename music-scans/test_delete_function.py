#!/usr/bin/env python
"""Test the delete function to see why it's not finding MakelaraVicharamu"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
KALPANA_SWARA_SONGS_DIR = BASE_DIR / "songs"

def _delete_kalpana_swara_song(song_id):
    """Delete a KalpanaSwaramComposer song file from songs/ folder by ID"""
    print(f"\nAttempting to delete song with ID: {song_id}\n")
    
    if not KALPANA_SWARA_SONGS_DIR.exists():
        print("ERROR: Songs directory does not exist")
        return False
    
    try:
        for song_file in KALPANA_SWARA_SONGS_DIR.glob("*.json"):
            try:
                print(f"Checking file: {song_file.name}")
                with open(song_file, 'r', encoding='utf-8') as f:
                    song_data = json.load(f)
                    file_id = song_data.get('id')
                    file_name = song_data.get('name', 'Unknown')
                    print(f"  - ID: {file_id[:8] if file_id else 'None'}...")
                    print(f"  - Name: {file_name}")
                    
                    if file_id == song_id:
                        print(f"\n✓ Found matching song! Would delete: {song_file.name}")
                        # Uncomment to actually delete:
                        # song_file.unlink()
                        return True
            except json.JSONDecodeError as je:
                print(f"  ERROR: Failed to parse JSON: {je}")
                continue
            except Exception as e:
                print(f"  ERROR: {e}")
                continue
        
        print(f"\n✗ Song with ID {song_id} not found in any file")
    except Exception as e:
        print(f"ERROR: {e}")
    
    return False

# Test with MakelaraVicharamu's ID
test_id = "d7263d81-1b27-4974-82c1-3de3e1a1efb9"
print("=" * 60)
print("Testing DELETE function with MakelaraVicharamu ID")
print("=" * 60)
result = _delete_kalpana_swara_song(test_id)
print(f"\nResult: {result}")
