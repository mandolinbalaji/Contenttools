# Code Review - Unwanted Methods and Lines

## KANAKKU.HTML

### Console Logging Statements (Lines to Remove)
These debug statements should be removed from production:

1. **Line 1605**: `console.log('[Save] Generated MIDI base64 data...')`
2. **Line 1607**: `console.warn('[Save] getMidiFileData returned null')`
3. **Line 1610**: `console.log('[Save] No currentMidiData - MIDI not saved...')`
4. **Line 1633**: `console.log('[Save] Success:', saved)`
5. **Line 1640**: `console.error('[Save] Server error:', error)` - Can stay (error logging)
6. **Line 1644**: `console.error('Save error:', err)` - Can stay (error logging)
7. **Line 1820**: `console.log('Loaded kanakkus:', data)`
8. **Line 1919**: `console.error('Delete error:', err)` - Can stay (error logging)
9. **Line 1944**: `console.error('Error opening MIDI:', err)` - Can stay (error logging)
10. **Line 1976**: `console.error('Error loading kanakkus:', err)` - Can stay (error logging)
11. **Line 2477**: `console.log('MIDI generated and ready to save')`
12. **Line 2488**: `console.log('Open MIDI clicked. currentMidiData:', currentMidiData)`

**Recommendation**: Remove lines 1605, 1607, 1610, 1633, 1820, 2477, 2488 (debug info logs). Keep error logs for troubleshooting.

---

## APP.PY

### Startup Logging Statements (Informational - Can Keep or Move)
1. **Line 18**: `print("[WARNING] speech_recognition library not installed...")` - OK (important warning)
2. **Line 23**: `print(f"[STARTUP] BASE_DIR: {BASE_DIR}")` - Consider removing
3. **Line 24**: `print(f"[STARTUP] Script location: {Path(__file__).absolute()}")` - Consider removing

### Request/Response Logging Middleware (Lines 37-50)
The middleware logs every request and response. This is good for debugging but can be verbose in production. Consider making this conditional based on environment.

### MIDI Validation Debug Logging
Lines with `[DEBUG]`, `[INFO]`, `[ERROR]` prefixes:
- **Line 313**: `print(f"[DEBUG] File hex (first 60 bytes)...")` - Debug statement, remove in production
- **Line 316**: `print(f"[INFO] MIDI validation passed...")` - Informational, can remove
- **Line 328**: `print(f"[INFO] Saved MIDI file...")` - Informational, can remove
- **Line 331**: `print(f"[ERROR] Failed to save MIDI file...")` - OK, keep for errors

### Audio Testing Debug Statements
- **Line 453**: `print(f"[DEBUG] Saved test audio...")` - Debug statement, remove
- **Line 461**: `print(f"[ERROR] Test audio error...")` - Keep for errors

### Transcription Comparison Debug Statements (Lines 576-578, 624)
These are within test endpoints and should be removed or moved to proper logging:
- **Line 576-577**: `print(f"\n{'='*70}")` - Debug formatting
- **Line 577**: `print(f"[COMPARE] Testing: {filename}")` - Debug info
- **Line 578**: `print(f"{'='*70}")` - Debug formatting
- **Line 624**: `print(f"[COMPARE] Google transcription...")` - Debug info

### Test/Debug Endpoints (Consider Removing)
1. **Lines 440-462**: `/api/test-audio` endpoint - This is a test endpoint that should be removed from production
2. **Lines 568-647**: `/api/transcribe-with-corrections` endpoint - Test/comparison endpoint
3. **Lines 655-762**: `/api/test-transcribe` endpoint - Debug/test endpoint

**Recommendation**: Wrap test endpoints with environment check or remove them entirely

### Request Logging with sys.stderr (Lines 37-50)
The middleware tries to write to stderr which may fail silently:
```python
@app.before_request
def log_request():
    import sys
    try:
        sys.stderr.write(f"\n[REQUEST] {request.method} {request.path}\n")
        sys.stderr.flush()
    except:
        pass
```

This is inefficient (importing sys in every request) and catches all exceptions. Consider using proper Flask logging instead.

---

## SUMMARY OF RECOMMENDATIONS

### KANAKKU.HTML
Remove or comment these debug console.log statements:
- Lines: 1605, 1607, 1610, 1633, 1820, 2477, 2488

**Total**: 7 debug statements to remove

### APP.PY
Remove or make conditional:
1. Lines 23-24: Startup logging (informational only)
2. Line 313: MIDI hex debug
3. Lines 316, 328: MIDI info logging
4. Line 453: Test audio debug
5. Lines 576-578, 624: Transcription debug output
6. Lines 440-462: Remove `/api/test-audio` endpoint or wrap with env check
7. Lines 568-647: Remove `/api/transcribe-with-corrections` endpoint or wrap with env check
8. Lines 655-762: Remove `/api/test-transcribe` endpoint or wrap with env check
9. Lines 37-50: Replace stderr logging with proper Flask logger

**Total**: ~15 debug statements + 3 test endpoints to review

### Code Quality Improvements
1. Use proper logging module instead of print() statements
2. Use environment variables to control debug output
3. Remove test endpoints from production code or hide behind feature flags
4. Improve error handling (catch-all `except:` statements)

### Files to Clean
- `app.py`: Main cleanup needed
- `Kanakku.html`: Minor cleanup (console logs)
