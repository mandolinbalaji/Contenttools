#!/usr/bin/env python
"""Simulate what the GET endpoint returns for all songs"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
KALPANA_SWARA_SONGS_DIR = BASE_DIR / "songs"

def _load_kalpana_swara_songs():
    """Load all KalpanaSwaramComposer songs from songs/ folder"""
    songs = []
    if not KALPANA_SWARA_SONGS_DIR.exists():
        return songs
    try:
        for song_file in KALPANA_SWARA_SONGS_DIR.glob("*.json"):
            try:
                with open(song_file, 'r', encoding='utf-8') as f:
                    song_data = json.load(f)
                    # Only add valid songs with a name
                    if song_data.get('name'):
                        songs.append(song_data)
            except Exception as e:
                print(f"Error loading {song_file.name}: {e}")
                continue
        # Sort by lastModified in descending order
        songs.sort(key=lambda s: s.get('lastModified', ''), reverse=True)
    except Exception as e:
        print(f"Error loading songs: {e}")
        return []
    return songs

print("Loading songs from backend endpoint...\n")
songs = _load_kalpana_swara_songs()

print(f"Loaded {len(songs)} songs:\n")
for song in songs:
    print(f"Song: {song.get('name')}")
    print(f"  ID: {song.get('id')}")
    print()
