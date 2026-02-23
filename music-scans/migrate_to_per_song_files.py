#!/usr/bin/env python3
"""
Migration Script: Split notation-composer.json to per-song files
Purpose: Convert monolithic JSON (8,586 lines) → per-song structure
Date: February 23, 2026
"""

import json
import os
from pathlib import Path
from datetime import datetime
import shutil

# Configuration
NOTATION_FILE = "notation-composer.json"
BACKUP_DIR = "backups"
METADATA_DIR = "metadata"
SONGS_DIR = "songs"
REFERENCE_FILE = os.path.join(METADATA_DIR, "reference-data.json")
REPORT_FILE = "migration_report.txt"

def log_message(msg, report_file):
    """Print to console and append to report file"""
    print(msg)
    with open(report_file, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def create_backup(notation_file, backup_dir):
    """Create backup of original notation-composer.json"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_filename = f"notation-composer.json.backup.{timestamp}"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy(notation_file, backup_path)
    
    return backup_path

def create_directories():
    """Create metadata and songs directories"""
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(SONGS_DIR, exist_ok=True)

def extract_metadata(data):
    """
    Extract metadata from first object in array
    Original structure: [metadata_obj, song1_obj, song2_obj, ...]
    """
    if not data or len(data) == 0:
        return None
    
    metadata_obj = data[0]
    
    # Extract only the metadata section
    if "_metadata" in metadata_obj:
        return {
            "_metadata": metadata_obj["_metadata"],
            "version": metadata_obj.get("version", "1.0"),
            "description": "MIDI Note Octave and Sruthi Mapping Reference"
        }
    
    return {
        "_metadata": {
            "version": "1.0",
            "description": "MIDI Note Octave and Sruthi Mapping Reference",
            "octaveMarkers": metadata_obj.get("_metadata", {}).get("octaveMarkers", {}),
            "sruthiMappings": metadata_obj.get("_metadata", {}).get("sruthiMappings", {})
        }
    }

def extract_songs(data):
    """
    Extract all songs from array
    Skip if it looks like metadata (has _metadata but is not a song)
    Songs have 'sections' field (list of section objects with atoms)
    """
    songs = []
    song_count = 0
    
    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            continue
        
        # Check if this is a song (has 'name' and 'sections' field)
        has_sections = isinstance(obj.get("sections"), list)
        has_name = "name" in obj
        
        if has_name and has_sections:
            songs.append(obj)
            song_count += 1
    
    return songs, song_count

def sanitize_filename(name):
    """Convert song name to valid filename"""
    # Remove spaces, special chars, keep alphanumeric
    return "".join(c for c in name if c.isalnum() or c in ['-', '_']).rstrip()

def save_song_file(song, songs_dir):
    """Save individual song to songs/{SongName}.json"""
    song_name = song.get("name", "UnknownSong")
    safe_name = sanitize_filename(song_name)
    filepath = os.path.join(songs_dir, f"{safe_name}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(song, f, indent=2, ensure_ascii=False)
    
    return filepath, safe_name

def create_index(songs, songs_dir):
    """
    Create new INDEX file (notation-composer.json)
    Contains: thin references to each song file
    """
    index = []
    
    for song in songs:
        safe_name = sanitize_filename(song.get("name", "UnknownSong"))
        
        # Create thin reference
        song_ref = {
            "id": song.get("id", "unknown"),
            "name": song.get("name", "Unknown"),
            "ragam": song.get("ragam", ""),
            "thalam": song.get("thalam", ""),
            "composer": song.get("composer", ""),
            "sruthi": song.get("sruthi", ""),
            "file": f"songs/{safe_name}.json"
        }
        
        index.append(song_ref)
    
    return index

def count_atoms(songs):
    """Count total number of atoms across all songs"""
    total_atoms = 0
    for song in songs:
        # Songs have 'sections' field (list of dictionaries)
        sections = song.get("sections", [])
        for section in sections:
            if isinstance(section, dict):
                atoms = section.get("atoms", [])
                if isinstance(atoms, list):
                    total_atoms += len(atoms)
    
    return total_atoms

def verify_json_files():
    """Verify all created JSON files are valid"""
    all_valid = True
    
    # Check notation-composer.json (index)
    try:
        with open(NOTATION_FILE, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ {NOTATION_FILE} - Valid JSON")
    except Exception as e:
        print(f"❌ {NOTATION_FILE} - Invalid JSON: {e}")
        all_valid = False
    
    # Check reference-data.json
    try:
        with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ {REFERENCE_FILE} - Valid JSON")
    except Exception as e:
        print(f"❌ {REFERENCE_FILE} - Invalid JSON: {e}")
        all_valid = False
    
    # Check all song files
    for filename in os.listdir(SONGS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SONGS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✅ {filepath} - Valid JSON")
            except Exception as e:
                print(f"❌ {filepath} - Invalid JSON: {e}")
                all_valid = False
    
    return all_valid

def main():
    """Main migration workflow"""
    
    # Initialize report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Migration Report\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"=" * 50 + "\n\n")
    
    print("\n" + "=" * 50)
    print("Per-Song JSON File Structure Migration")
    print("=" * 50 + "\n")
    
    # Step 1: Load original file
    print("📂 Step 1: Loading original notation-composer.json...")
    try:
        with open(NOTATION_FILE, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        log_message(f"✅ Loaded {NOTATION_FILE}", REPORT_FILE)
        log_message(f"   Objects in file: {len(original_data)}", REPORT_FILE)
    except Exception as e:
        log_message(f"❌ Error loading {NOTATION_FILE}: {e}", REPORT_FILE)
        return False
    
    # Step 2: Create backup
    print("💾 Step 2: Creating backup...")
    try:
        backup_path = create_backup(NOTATION_FILE, BACKUP_DIR)
        log_message(f"✅ Backup created: {backup_path}", REPORT_FILE)
    except Exception as e:
        log_message(f"❌ Error creating backup: {e}", REPORT_FILE)
        return False
    
    # Step 3: Extract metadata
    print("📋 Step 3: Extracting metadata...")
    try:
        metadata = extract_metadata(original_data)
        log_message(f"✅ Metadata extracted", REPORT_FILE)
    except Exception as e:
        log_message(f"❌ Error extracting metadata: {e}", REPORT_FILE)
        return False
    
    # Step 4: Extract songs
    print("🎵 Step 4: Extracting songs...")
    try:
        songs, song_count = extract_songs(original_data)
        total_atoms = count_atoms(songs)
        log_message(f"✅ Extracted {song_count} songs with {total_atoms} total atoms", REPORT_FILE)
        print(f"   Songs extracted: {song_count}")
        print(f"   Total atoms: {total_atoms}")
    except Exception as e:
        import traceback
        log_message(f"❌ Error extracting songs: {e}", REPORT_FILE)
        log_message(f"Traceback: {traceback.format_exc()}", REPORT_FILE)
        return False
    
    # Step 5: Create directories
    print("📁 Step 5: Creating directories...")
    try:
        create_directories()
        log_message(f"✅ Directories created: {METADATA_DIR}/, {SONGS_DIR}/", REPORT_FILE)
    except Exception as e:
        log_message(f"❌ Error creating directories: {e}", REPORT_FILE)
        return False
    
    # Step 6: Save reference data
    print("📝 Step 6: Saving reference data...")
    try:
        with open(REFERENCE_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log_message(f"✅ Reference data saved: {REFERENCE_FILE}", REPORT_FILE)
    except Exception as e:
        log_message(f"❌ Error saving reference data: {e}", REPORT_FILE)
        return False
    
    # Step 7: Save individual song files
    print("🎼 Step 7: Saving individual song files...")
    saved_songs = []
    try:
        for i, song in enumerate(songs, 1):
            try:
                if not isinstance(song, dict):
                    raise ValueError(f"Song {i} is not a dictionary: {type(song)}")
                
                filepath, safe_name = save_song_file(song, SONGS_DIR)
                saved_songs.append(safe_name)
                song_name = song.get("name", "Unknown")
                song_atoms = 0
                for section in song.get("sections", []):
                    if isinstance(section, dict):
                        song_atoms += len(section.get("atoms", []))
                print(f"   [{i}/{song_count}] {song_name} ({song_atoms} atoms) → {filepath}")
                log_message(f"   ✅ Saved: {song_name} → {filepath}", REPORT_FILE)
            except Exception as inner_e:
                import traceback
                log_message(f"   ❌ Error saving song {i}: {inner_e}", REPORT_FILE)
                log_message(f"      Traceback: {traceback.format_exc()}", REPORT_FILE)
                raise
    except Exception as e:
        import traceback
        log_message(f"❌ Error saving song files: {e}", REPORT_FILE)
        log_message(f"Traceback: {traceback.format_exc()}", REPORT_FILE)
        return False
    
    # Step 8: Create new index file
    print("📇 Step 8: Creating new index file...")
    try:
        index = create_index(songs, SONGS_DIR)
        with open(NOTATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        log_message(f"✅ Index file created: {NOTATION_FILE} ({len(index)} entries)", REPORT_FILE)
        print(f"   Index entries: {len(index)}")
    except Exception as e:
        log_message(f"❌ Error creating index file: {e}", REPORT_FILE)
        return False
    
    # Step 9: Verify JSON files
    print("✔️  Step 9: Verifying JSON files...")
    try:
        all_valid = verify_json_files()
        if all_valid:
            log_message(f"✅ All JSON files valid", REPORT_FILE)
        else:
            log_message(f"⚠️  Some JSON files have issues", REPORT_FILE)
    except Exception as e:
        log_message(f"❌ Error verifying files: {e}", REPORT_FILE)
        return False
    
    # Final summary
    print("\n" + "=" * 50)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 50)
    log_message(f"\n✅ Migration completed successfully!", REPORT_FILE)
    log_message(f"\nSummary:", REPORT_FILE)
    log_message(f"  - Original file: {NOTATION_FILE}", REPORT_FILE)
    log_message(f"  - Backup: {BACKUP_DIR}/notation-composer.json.backup.*", REPORT_FILE)
    log_message(f"  - New index: {NOTATION_FILE} (thin references)", REPORT_FILE)
    log_message(f"  - Metadata: {REFERENCE_FILE}", REPORT_FILE)
    log_message(f"  - Song files: {SONGS_DIR}/ ({song_count} files)", REPORT_FILE)
    log_message(f"  - Total atoms preserved: {total_atoms}", REPORT_FILE)
    
    print(f"\nFiles created:")
    print(f"  ✅ {NOTATION_FILE} (INDEX)")
    print(f"  ✅ {REFERENCE_FILE}")
    for saved_song in saved_songs:
        print(f"  ✅ {SONGS_DIR}/{saved_song}.json")
    
    print(f"\nNext steps:")
    print(f"  1. Run: python verify_migration.py")
    print(f"  2. Update app.py functions")
    print(f"  3. Test app in browser")
    print(f"\nReport saved to: {REPORT_FILE}")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
