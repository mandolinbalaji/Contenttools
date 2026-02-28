#!/usr/bin/env python
"""Get the FULL ID from MakelaraVicharamu.json"""

import json

with open('songs/MakelaraVicharamu.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print("Full ID:", data.get('id'))
    print("Song Name:", data.get('name'))
