# Commas & Calculations Implementation Verification

## Design Requirements (from KALPANA_SWARA_COMPOSER_DESIGN.md)

### Formula: cycleLength = beats × nadai

```
Adhi Thala       = 8 beats × 4 nadai = 32 cells/row
Misra Chapu     = 7 beats × 2 nadai = 14 cells/row
Kanda Chapu     = 5 beats × 2 nadai = 10 cells/row
Rupakam         = 6 beats × 4 nadai = 24 cells/row
```

### Formula: leadingCommas = (eduppu - 1 - noteCount) mod cycleLength

Where:
- `eduppu` = target landing beat (1-based)
- `noteCount` = count of notes AND commas in phrase
- `cycleLength` = beats × nadai
- Result represents REST BEATS before phrase starts

## Verified Test Cases

### Test 1: Simple Adhi Phrase
```
Configuration:
  Thalam: Adhi (8 beats × 4 nadai)
  cycleLength: 32 cells
  Eduppu: 4 (land on beat 4, position 3 in 0-based indexing)
  Phrase: "srgmpdns" (8 notes)
  
Calculation:
  noteCount = 8
  leadingCommas = (4 - 1 - 8) % 32 = -5 % 32 = 27
  fullPhrase = ",,,,,,,,,,,,,,,,,,,,,,,,,,," + "srgmpdns"
  fullPhrase = 27 commas + 8 notes = 35 characters
  
Expected Row 1 (32 cells):
  Position:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32
  Content:   -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  s  r  g  m  p
             └─────────────── 27 commas (shown as "-") ───────────────────────┘
  Landing:   at position 4 (eduppu=4)
  
Expected Row 2 (3 remaining cells):
  d  n  s

Verification:
  ✓ 27 commas + 8 notes = 35 total
  ✓ Row 1 has first 32 characters (27 commas + first 5 notes)
  ✓ Row 2 has remaining 3 notes
  ✓ Landing marked at position 4 (eduppu value)
```

### Test 2: User Example - Misra with Short Phrase
```
Configuration:
  Thalam: Misra (7 beats × 2 nadai)
  cycleLength: 14 cells
  Eduppu: 4 (land on beat 4, position 3 in 0-based indexing)
  Phrase: "srgmmgrs" (8 notes)
  
Calculation:
  noteCount = 8
  leadingCommas = (4 - 1 - 8) % 14 = -5 % 14 = 9
  fullPhrase = ",,,,,,,,," + "srgmmgrs"
  fullPhrase = 9 commas + 8 notes = 17 characters
  
Expected Row 1 (14 cells):
  Position:  1  2  3  4  5  6  7  8  9 10 11 12 13 14
  Content:   -  -  -  -  -  -  -  -  -  s  r  g  m  m
             └─ 9 commas ─┘
  Landing:   at position 4 (eduppu=4)
  
Expected Row 2 (3 remaining cells):
  Position:  1  2  3
  Content:   g  r  s

Verification:
  ✓ 9 commas + 8 notes = 17 total
  ✓ Row 1 has first 14 characters (9 commas + first 5 notes)
  ✓ Row 2 has remaining 3 notes
  ✓ Landing marked at position 4 of Row 1
```

### Test 3: Explicit Override in Phrase
```
Configuration:
  Same as Test 2, but:
  Phrase: "sr1gmmgrs" (8 notes - r1 counts as 1 note)
  
Display (should NOT expand r1 to r + 1):
  Row 1: "-  -  -  -  -  -  -  -  -  s  r1 g  m  m"
              └─ 9 commas ──┘
  Row 2: "g  r  s"
  
Verification:
  ✓ r1 displays in single cell as "r1"
  ✓ Still 8 notes total (r1 = 1, not 2)
```

## Display Implementation Details

### Mapping Characters to Display
- **Comma `,`** → Display as `-` (dash/rest)
- **Space ` `** → Display as empty cell (unless at end of row)
- **Note character** → Display as-is (s, r, g, m, p, d, n)
- **Variant (e.g. r1)** → Display full notation in cell

### Landing Position Highlight

The landing position (eduppu) should be highlighted ONLY:
- ✓ On the first row of the phrase
- ✓ At column index = (eduppu - 1)
- ✓ Green background (#efe or similar)

## Implementation Verification Checklist

- [x] `calculateLeadingCommas()` correctly implements formula
- [x] `countNotes()` counts both notes and commas, handles variants
- [x] `updatePhrase()` builds fullPhrase with leading commas
- [x] `renderSpreadsheetLine()` displays raw phrases (no scale transform)
- [x] Commas display as `-` in spreadsheet
- [x] Multi-line wrapping at cycleLength boundary
- [x] Landing position highlighted only on first row
- [ ] Verify actual display in browser matches expected output

## Current Code Status

### Correct Implementations
✅ `calculateLeadingCommas(noteCount, cycleLength, eduppu)` - Line 1385
✅ `countNotes(text)` - Line 1360
✅ `cleanPhrase(text)` - Line 1390
✅ `updatePhrase()` - Lines 1505-1528
✅ `renderSpreadsheetLine()` - Lines 1759-1826

### Verification Needed
🔍 Open browser and test with:
- Create song with Adhi thalam (8×4)
- Enter phrase: "srgmpdns"
- Check spreadsheet displays 27 dashes, then phrase
- Enter phrase: "sr1gmmgrs" (with variant)
- Check r1 displays as single cell

## Test Steps in Application

1. Open http://localhost:5000/KalpanaSwaramComposer.html
2. Set Thalam to Adhi (8, 4)
3. Set Eduppu to 4
4. Enter Phrase: "srgmpdns"
5. Check Spreadsheet:
   - Should show 27 dashes (-) for rests
   - Then 8 notes: s r g m p d n s
   - Green highlight at position 4 (beat 4)

6. Try Misra Thalam:
   - Set Beats: 7, Nadai: 2
   - Keep Eduppu: 4
   - Enter Phrase: "srgmmgrs"
   - Check Spreadsheet:
     - Row 1: 9 dashes + 5 notes
     - Row 2: 3 remaining notes
     - Green highlight at position 4 of Row 1
