#!/usr/bin/env python3
"""
Verification Script: Validate per-song file migration
Purpose: Ensure data integrity and file structure after migration
Date: February 23, 2026
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# Configuration
NOTATION_FILE = "notation-composer.json"
METADATA_DIR = "metadata"
SONGS_DIR = "songs"
REFERENCE_FILE = os.path.join(METADATA_DIR, "reference-data.json")
REPORT_FILE = "verify_migration_report.txt"

def log_message(msg, report_file):
    """Print to console and append to report file"""
    print(msg)
    with open(report_file, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def verify_files_exist():
    """Check if all required files exist"""
    checks = {
        NOTATION_FILE: os.path.exists(NOTATION_FILE),
        REFERENCE_FILE: os.path.exists(REFERENCE_FILE),
        SONGS_DIR: os.path.isdir(SONGS_DIR),
        METADATA_DIR: os.path.isdir(METADATA_DIR)
    }
    
    all_exist = all(checks.values())
    
    return checks, all_exist

def verify_json_syntax():
    """Verify all JSON files have valid syntax"""
    syntax_errors = []
    valid_files = []
    
    # Check index
    try:
        with open(NOTATION_FILE, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        valid_files.append(NOTATION_FILE)
    except Exception as e:
        syntax_errors.append((NOTATION_FILE, str(e)))
    
    # Check reference
    try:
        with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
            ref_data = json.load(f)
        valid_files.append(REFERENCE_FILE)
    except Exception as e:
        syntax_errors.append((REFERENCE_FILE, str(e)))
    
    # Check all song files
    if os.path.isdir(SONGS_DIR):
        for filename in os.listdir(SONGS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(SONGS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        json.load(f)
                    valid_files.append(filepath)
                except Exception as e:
                    syntax_errors.append((filepath, str(e)))
    
    return valid_files, syntax_errors

def count_atoms_in_data(data):
    """Count atoms in song data"""
    if isinstance(data, dict) and "sections" in data:
        total = 0
        for section in data.get("sections", []):
            if isinstance(section, dict):
                atoms = section.get("atoms", [])
                if isinstance(atoms, list):
                    total += len(atoms)
        return total
    return 0

def verify_data_integrity():
    """Verify data wasn't lost during migration"""
    integrity_issues = []
    song_stats = []
    
    # Load index
    try:
        with open(NOTATION_FILE, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except:
        return None, ["Could not load index file"]
    
    total_atoms = 0
    enriched_atoms = 0
    
    # Check each song in index
    for song_ref in index_data:
        song_file = song_ref.get("file", "")
        song_name = song_ref.get("name", "Unknown")
        
        # Load actual song file
        if not os.path.exists(song_file):
            integrity_issues.append(f"Missing file: {song_file} (referenced in index)")
            continue
        
        try:
            with open(song_file, 'r', encoding='utf-8') as f:
                song_data = json.load(f)
        except Exception as e:
            integrity_issues.append(f"Cannot load {song_file}: {e}")
            continue
        
        # Count atoms
        song_atoms = count_atoms_in_data(song_data)
        total_atoms += song_atoms
        
        # Count enriched atoms (have frequency field)
        enriched_in_song = 0
        for section in song_data.get("sections", []):
            if isinstance(section, dict):
                for atom in section.get("atoms", []):
                    if isinstance(atom, dict) and "frequency" in atom and atom.get("frequency") is not None:
                        enriched_in_song += 1
        enriched_atoms += enriched_in_song
        
        # Check required fields
        required_fields = ["id", "name", "sections", "sruthi"]
        missing_fields = []
        for field in required_fields:
            if field not in song_data:
                missing_fields.append(field)
        
        if missing_fields:
            integrity_issues.append(f"{song_name}: Missing fields: {missing_fields}")
        
        song_stats.append({
            "name": song_name,
            "atoms": song_atoms,
            "enriched": enriched_in_song,
            "file": song_file
        })
    
    return {
        "total_atoms": total_atoms,
        "enriched_atoms": enriched_atoms,
        "song_stats": song_stats,
        "songs": len(song_stats)
    }, integrity_issues

def verify_no_duplicates():
    """Check for duplicate data across files"""
    duplicates = []
    
    # Check: reference data should not contain song-specific data
    try:
        with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
            ref_data = json.load(f)
        
        # Reference should only have _metadata and version, no songs
        if "sections" in str(ref_data):
            duplicates.append("Reference file contains song data (sections)")
        if "atoms" in str(ref_data):
            duplicates.append("Reference file contains atom data")
    except:
        pass
    
    # Check: no duplicate sruthiLookupTables
    sruthi_lookups = []
    if os.path.isdir(SONGS_DIR):
        for filename in os.listdir(SONGS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(SONGS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        song_data = json.load(f)
                    
                    metadata = song_data.get("_metadata", {})
                    if "sruthiLookupTable" in metadata:
                        sruthi_lookups.append(filename)
                except:
                    pass
    
    if len(sruthi_lookups) > 1:
        duplicates.append(f"Multiple files with sruthiLookupTable: {sruthi_lookups}")
    
    return duplicates

def verify_enrichment_fields():
    """Verify enrichment fields are preserved"""
    required_enrichment_fields = [
        "frequency", "midiNumber", "ragaswaraEquivalent", 
        "sruthiNoteEquivalent", "isRest", "sruthi"
    ]
    
    coverage = defaultdict(lambda: {"present": 0, "total": 0})
    
    if os.path.isdir(SONGS_DIR):
        for filename in os.listdir(SONGS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(SONGS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        song_data = json.load(f)
                    
                    song_name = song_data.get("name", filename)
                    
                    for section in song_data.get("sections", []):
                        if isinstance(section, dict):
                            atoms = section.get("atoms", [])
                            if isinstance(atoms, list):
                                for atom in atoms:
                                    if isinstance(atom, dict):
                                        for field in required_enrichment_fields:
                                            coverage[song_name]["total"] += 1
                                            if field in atom and atom[field] is not None:
                                                coverage[song_name]["present"] += 1
                except:
                    pass
    
    return coverage

def main():
    """Main verification workflow"""
    
    # Initialize report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("Migration Verification Report\n")
        f.write("=" * 50 + "\n\n")
    
    print("\n" + "=" * 50)
    print("Migration Verification")
    print("=" * 50 + "\n")
    
    all_checks_passed = True
    
    # Check 1: Files exist
    print("📂 Check 1: Verifying files exist...")
    files_check, files_exist = verify_files_exist()
    for filepath, exists in files_check.items():
        status = "✅" if exists else "❌"
        log_message(f"   {status} {filepath}", REPORT_FILE)
        if not exists:
            all_checks_passed = False
    
    # Check 2: JSON syntax
    print("\n🔍 Check 2: Verifying JSON syntax...")
    valid_files, syntax_errors = verify_json_syntax()
    log_message(f"   Valid files: {len(valid_files)}", REPORT_FILE)
    for filepath in valid_files:
        log_message(f"   ✅ {filepath}", REPORT_FILE)
    
    if syntax_errors:
        all_checks_passed = False
        for filepath, error in syntax_errors:
            log_message(f"   ❌ {filepath}: {error}", REPORT_FILE)
    
    # Check 3: Data integrity
    print("\n📊 Check 3: Verifying data integrity...")
    integrity_data, integrity_issues = verify_data_integrity()
    
    if integrity_data:
        log_message(f"   Total atoms: {integrity_data['total_atoms']}", REPORT_FILE)
        log_message(f"   Enriched atoms: {integrity_data['enriched_atoms']}", REPORT_FILE)
        log_message(f"   Songs: {integrity_data['songs']}", REPORT_FILE)
        print(f"   Total atoms: {integrity_data['total_atoms']}")
        print(f"   Enriched atoms: {integrity_data['enriched_atoms']}")
        print(f"   Songs: {integrity_data['songs']}")
        
        for song_stat in integrity_data['song_stats']:
            log_message(f"   ✅ {song_stat['name']}: {song_stat['atoms']} atoms ({song_stat['enriched']} enriched)", REPORT_FILE)
            print(f"      {song_stat['name']}: {song_stat['atoms']} atoms ({song_stat['enriched']} enriched)")
    
    if integrity_issues:
        all_checks_passed = False
        for issue in integrity_issues:
            log_message(f"   ❌ {issue}", REPORT_FILE)
    
    # Check 4: No duplicates
    print("\n🔄 Check 4: Checking for duplicate data...")
    duplicates = verify_no_duplicates()
    if not duplicates:
        log_message(f"   ✅ No duplicate data found", REPORT_FILE)
        print(f"   ✅ No duplicate data found")
    else:
        all_checks_passed = False
        for dup in duplicates:
            log_message(f"   ❌ {dup}", REPORT_FILE)
    
    # Check 5: Enrichment fields
    print("\n🎵 Check 5: Verifying enrichment fields...")
    enrichment_coverage = verify_enrichment_fields()
    for song_name, coverage in enrichment_coverage.items():
        if coverage['total'] > 0:
            percent = round(100 * coverage['present'] / coverage['total'], 1)
            status = "✅" if percent >= 90 else "⚠️ "
            log_message(f"   {status} {song_name}: {percent}% fields enriched", REPORT_FILE)
            print(f"      {song_name}: {percent}% fields enriched")
    
    # Summary
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("✅ ALL VERIFICATION CHECKS PASSED")
        log_message(f"\n✅ All verification checks passed!", REPORT_FILE)
    else:
        print("⚠️  SOME VERIFICATION CHECKS FAILED")
        log_message(f"\n⚠️  Some verification checks failed!", REPORT_FILE)
    
    print("=" * 50)
    log_message(f"\nNext steps:", REPORT_FILE)
    log_message(f"  1. Update app.py functions: _load_notations(), _save_notations()", REPORT_FILE)
    log_message(f"  2. Add new functions: _get_song(), _save_song(), _delete_song_file()", REPORT_FILE)
    log_message(f"  3. Test app in browser", REPORT_FILE)
    log_message(f"\nReport saved to: {REPORT_FILE}", REPORT_FILE)
    
    print(f"\nReport: {REPORT_FILE}")
    
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
