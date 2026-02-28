#!/usr/bin/env python
"""Test the DELETE endpoint to see if it works"""

import json
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
SONGS_DIR = BASE_DIR / "songs"

API_BASE = "http://localhost:5000/api"

print("\n===== Testing DELETE Endpoint =====\n")

# First load all songs to get a song ID to delete
try:
    response = requests.get(f"{API_BASE}/kalpana-swara-songs")
    if response.status_code == 200:
        songs = response.json()
        print(f"✓ Loaded {len(songs)} songs from server\n")
        
        if len(songs) > 0:
            test_song = songs[0]  # Use first song for testing
            test_song_id = test_song['id']
            test_song_name = test_song.get('name', 'Unknown')
            
            print(f"Test 1: Attempting to delete song '{test_song_name}' (ID: {test_song_id[:8]}...)")
            print(f"Sending DELETE request to: {API_BASE}/kalpana-swara-songs/{test_song_id}\n")
            
            try:
                delete_response = requests.delete(f"{API_BASE}/kalpana-swara-songs/{test_song_id}")
                print(f"Response Status: {delete_response.status_code}")
                print(f"Response Headers: {dict(delete_response.headers)}")
                print(f"Response Body: {delete_response.text}\n")
                
                if delete_response.status_code == 200:
                    print("✓ DELETE request succeeded (200 status)")
                    print(f"Response JSON: {delete_response.json()}\n")
                    
                    # Check if song file was actually deleted
                    song_file_found = False
                    for song_file in SONGS_DIR.glob("*.json"):
                        try:
                            with open(song_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if data.get('id') == test_song_id:
                                    song_file_found = True
                                    print(f"✗ Song file still exists: {song_file.name}")
                                    break
                        except:
                            pass
                    
                    if not song_file_found:
                        print(f"✓ Song file was deleted from songs/ folder")
                else:
                    print(f"✗ DELETE failed with status {delete_response.status_code}")
                    print(f"Response: {delete_response.json()}")
                    
            except Exception as e:
                print(f"✗ Error while making DELETE request: {e}")
        else:
            print("✗ No songs available to test deletion")
    else:
        print(f"✗ Failed to load songs: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to server at http://localhost:5000")
    print("   Make sure the Flask server is running!")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n===== Test Complete =====\n")
