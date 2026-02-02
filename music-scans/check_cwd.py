#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Check current working directory
print("Current working directory:", os.getcwd())
print("Python executable:", sys.executable)
print("Python version:", sys.version)

# Check if app.py exists
app_py = Path("app.py")
print(f"\napp.py exists in current dir: {app_py.exists()}")

# Check lessons.json in different ways
base_dir_1 = Path(r"g:\My Drive\ContentTools\music-scans")
lessons_file_1 = base_dir_1 / "lessons.json"
print(f"\nMethod 1 - Full path: {lessons_file_1}")
print(f"  Exists: {lessons_file_1.exists()}")

base_dir_2 = Path.cwd()
lessons_file_2 = base_dir_2 / "lessons.json"
print(f"\nMethod 2 - CWD: {lessons_file_2}")
print(f"  Exists: {lessons_file_2.exists()}")

# List files in current directory
print("\nFiles in current directory:")
for f in sorted(Path(".").glob("*")):
    if f.is_file():
        print(f"  {f.name}")
