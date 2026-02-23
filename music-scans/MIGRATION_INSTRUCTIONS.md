# Per-Song JSON File Structure: Migration Instructions

**Date**: February 23, 2026  
**Status**: IMPLEMENTATION IN PROGRESS  
**Owner**: AI Assistant + Developer

---

## QUICK START

```bash
# Step 1: Create directories
mkdir metadata songs

# Step 2: Run migration script
python migrate_to_per_song_files.py

# Step 3: Verify migration
python verify_migration.py

# Step 4: Update backend (app.py)
# - Modify _load_notations()
# - Modify _save_notations() 
# - Add _get_song(), _save_song(), _delete_song_file()

# Step 5: Test frontend
# - Load app, click Format, Save, Delete

# Step 6: Git commit
git add -A
git commit -m "migration: split notation-composer.json to per-song files"
```

---

## PHASE 1: BACKUP & PREPARE

### 1.1 Backup Current File
```bash
# Create backup
cp notation-composer.json backups/notation-composer.json.backup.20260223
```
✅ **Status**: Ready to execute

### 1.2 Create Directory Structure
```bash
mkdir -p metadata
mkdir -p songs
```
✅ **Status**: Ready to execute

### 1.3 Extract Shared Metadata
- Extract first object from notation-composer.json (lines 1-150)
- Save to: `metadata/reference-data.json`
- Contains: octaveMarkers, sruthiMappings, version info

✅ **Status**: Will be done by migrate_to_per_song_files.py

---

## PHASE 2: SPLIT SONGS (MIGRATION SCRIPT)

### 2.1 Script: `migrate_to_per_song_files.py`

**Purpose**: Automated migration of monolithic JSON → per-song structure

**Input**: `notation-composer.json` (8,586 lines, 2 songs)

**Output**:
- `notation-composer.json` (INDEX - ~30 lines)
- `metadata/reference-data.json` (~150 lines)
- `songs/MakelaraVicharamu.json` (~5,300 lines)
- `songs/SujanaJeevana.json` (~2,300 lines)
- `migration_report.txt` (Log of execution)

**Execution**: `python migrate_to_per_song_files.py`

✅ **Status**: Script creation in progress → will execute immediately

---

## PHASE 3: VERIFY MIGRATION

### 3.1 Script: `verify_migration.py`

**Purpose**: Validate migration completed correctly

**Checks**:
1. All files created (notation-composer.json, metadata/, songs/)
2. JSON syntax valid (all files parse without error)
3. Data integrity:
   - Original atom count == new file atom count
   - All enrichment fields preserved
   - ragaswaraVariantMapping intact
4. Index references match actual song files

**Execution**: `python verify_migration.py`

✅ **Status**: Script creation to follow after migration

---

## PHASE 4: UPDATE BACKEND (app.py)

### 4.1 Functions to Modify

| Function | Lines | Action | Details |
|----------|-------|--------|---------|
| `_load_notations()` | 1638-1647 | Change to read index only | Return array of thin song refs |
| `_save_notations()` | 1648-1651 | Rename, save index only | Update index file only |
| GET `/api/notation-composer` | 1655-1657 | Use index (no change to API) | Return array of songs |
| POST `/api/notation-composer` | 1659-1702 | Use new `_save_song()` | Save individual song file |
| DELETE `/api/notation-composer/<id>` | 1703-1715 | Use new `_delete_song_file()` | Delete song file and update index |

### 4.2 New Functions to Add

```python
def _load_index():
    """Load index from notation-composer.json"""
    
def _save_index(index):
    """Save index to notation-composer.json"""
    
def _get_song(song_id):
    """Load individual song from songs/{name}.json"""
    
def _save_song(song):
    """Save individual song to songs/{name}.json and update index"""
    
def _delete_song_file(song_name):
    """Delete songs/{name}.json and update index"""
```

✅ **Status**: To be implemented after migration verification

---

## PHASE 5: UPDATE FRONTEND

### 5.1 Verification Checklist

**Frontend Functions (No changes needed):**
- ✅ `renderPlaylist()` - Calls GET /api/notation-composer (works with index)
- ✅ `saveSongInternal()` - POSTs to /api/notation-composer (handled by new backend)
- ✅ `loadSongIntoUI()` - Works with song object in memory
- ✅ `exportMidi()` - Uses currentSong (no file I/O)

**Status**: No code changes needed, just verify app works

---

## MIGRATION CHECKLIST

### Pre-Migration
- [ ] Backup created: `backups/notation-composer.json.backup.20260223`
- [ ] Directories created: `metadata/`, `songs/`
- [ ] Migration script ready: `migrate_to_per_song_files.py`

### During Migration
- [ ] Run: `python migrate_to_per_song_files.py`
- [ ] Check output files created
- [ ] Verify no errors in console

### Post-Migration Verification
- [ ] Run: `python verify_migration.py`
- [ ] All checks pass (data integrity, JSON syntax, file count)
- [ ] Old notation-composer.json replaced with INDEX version

### Backend Update (app.py)
- [ ] `_load_notations()` reads index only
- [ ] `_save_notations()` renamed/updated to save index only
- [ ] New `_get_song()` function works
- [ ] New `_save_song()` function works
- [ ] New `_delete_song_file()` function works
- [ ] API endpoints updated to use new functions
- [ ] No changes to API contract (endpoints unchanged)

### Frontend Testing
- [ ] App loads: `python app.py`
- [ ] Playlist renders (GET /api/notation-composer)
- [ ] Click song: loads into UI
- [ ] Format song: enriches data
- [ ] Save song: persists to songs/{name}.json
- [ ] Delete song: removes file and updates index
- [ ] Export MIDI: works correctly

### Final Verification
- [ ] All original functionality preserved
- [ ] No data loss (atom count, enrichment fields)
- [ ] File sizes reasonable (index ~30 lines, per-song ~5K lines)
- [ ] No duplicate data across files

### Git Commit
- [ ] Stage all changes: `git add -A`
- [ ] Commit: `git commit -m "migration: split notation-composer.json to per-song files"`
- [ ] Push: `git push origin master`

---

## ROLLBACK PROCEDURE

**If something goes wrong:**

```bash
# 1. Stop Flask server
# 2. Restore backup
cp backups/notation-composer.json.backup.20260223 notation-composer.json

# 3. Remove migration artifacts
rm -rf songs/
rm -rf metadata/

# 4. Restart Flask
python app.py

# 5. Verify original functionality
```

---

## FILES TO CREATE/MODIFY

### CREATE (Scripts)
- [ ] `migrate_to_per_song_files.py` - Do split operation
- [ ] `verify_migration.py` - Validate migration results

### MODIFY (Backend)
- [ ] `app.py` - Update I/O functions (Phase 4)

### VERIFY (Frontend)  
- [ ] `SongNotationComposer.html` - No changes needed, just test

### OUTPUT (From scripts)
- [ ] `notation-composer.json` - New INDEX version
- [ ] `metadata/reference-data.json` - Shared reference data
- [ ] `songs/MakelaraVicharamu.json` - Per-song file 1
- [ ] `songs/SujanaJeevana.json` - Per-song file 2
- [ ] `migration_report.txt` - Execution log

---

## SUCCESS CRITERIA

✅ All checks must pass:

1. **Data Integrity**
   - Original song count preserved (2 songs)
   - Atom count: 576 rich atoms in MakelaraVicharamu
   - 576 varied atoms in SujanaJeevana
   - All enrichment fields present (frequency, midiNumber, ragaswaraEquivalent, etc.)

2. **File Structure**
   - Index file: ~30 lines (thin objects)
   - Metadata file: ~150 lines (reference only)
   - Per-song files: 2 files, ~5K lines each
   - No duplicate data across files

3. **API Contract**
   - GET /api/notation-composer returns array
   - POST /api/notation-composer saves song
   - DELETE /api/notation-composer/{id} deletes song
   - **API never changes** ✅

4. **Functional Testing**
   - Load app → playlist renders
   - Click song → loads correctly
   - Format + Save → works
   - Delete → works
   - Export MIDI → works

---

## TIMELINE

**Day 1 (Feb 23)**
- [ ] Create and run migration script
- [ ] Verify migration successful
- [ ] Estimated time: 1 hour

**Day 2 (Feb 24)**
- [ ] Update app.py functions
- [ ] Test each endpoint
- [ ] Estimated time: 2 hours

**Day 3 (Feb 25)**
- [ ] Full integration testing
- [ ] Frontend verification
- [ ] Git commit and push
- [ ] Estimated time: 1 hour

**Total**: 4 hours of implementation work

---

## NOTES

- **API Contract Unchanged**: Frontend code needs NO changes
- **Backward Compatible**: Old app.py endpoints work as-is
- **Easy Rollback**: Backup available in backups/ folder
- **Git History**: Clean commits with clear messages
- **Scalable**: Can add unlimited songs without file size issues

---

**Next Action**: Execute Phase 1 (create backup) → Phase 2 (migration script) → Phase 3 (verify)
