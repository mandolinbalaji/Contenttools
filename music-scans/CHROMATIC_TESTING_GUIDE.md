# Chromatic Swara Variant Testing Guide

## Changes Implemented

### 1. **countNotes() Function Update**
- Now correctly handles chromatic variant notation (r1, r2, r3, g1-g3, m1-m2, d1-d3, n1-n3)
- Each variant counts as 1 note (e.g., r1 = 1 note, NOT 2 notes)
- Commas still count as 1 rest note

**Test Cases:**
```
Input: "srgmpdns" → Expected: 8 notes
Input: "sr1g2m1d2n2s" → Expected: 8 notes
Input: "s,rg,,m" → Expected: 5 notes (s, comma, r, g, comma, comma, m)
Input: "r1g2m1d2n2" → Expected: 5 notes
```

### 2. **Scale Definition Text Box**
- Location: Below Tags section in Metadata area
- Input format: Space or comma-separated variants, e.g., "r2 g2 m1 d2 n2"
- Saves/loads with song data
- Provides default variant mappings for swaras in the raga

**Manual Test Steps:**
1. Create a new song
2. Enter scale: "r2 g2 m1 d2 n2"  
3. Save the song
4. Refresh the page or load the song back
5. Verify scale field shows "r2 g2 m1 d2 n2"

### 3. **Scale Resolution Logic**
- `parseScale()`: Converts "r2 g2 m1 d2 n2" into {r: 'r2', g: 'g2', m: 'm1', d: 'd2', n: 'n2'}
- `resolvePhrase()`: Applies scale defaults with phrase-level overrides
- **Behavior:**
  - Bare swaras (r, g, m, d, n) use scale variants if defined
  - Swaras with explicit variants in phrase (like r1, g3) override scale for that note only
  - Fixed swaras (s, p) never get variants
  - Commas and spaces are preserved

**Manual Test Steps:**
1. Create song with scale "r2 g2 m1 d2 n2"
2. Enter phrase: "srgmpdns"
3. Check note count: should be 8
4. In spreadsheet, internal resolution should convert to "sr2g2m1pd2n2s"
5. Enter phrase with override: "sr1gm" 
6. Should resolve to "sr1g2m1p" (r1 override, g2 from scale, m1 from scale)

### 4. **Multi-Line Spreadsheet Wrapping**
- Row width = beats × nadai (cycleLength)
- Phrases automatically wrap to multiple rows if they exceed cycleLength
- Landing position (eduppu) highlighted only on first row
- Lyrics only shown on first row

**Manual Test Steps:**
1. Create song: Thalam=Adhi (8 beats), Nadai=4 → cycleLength=32
2. Set Eduppu=4
3. Enter phrase: "srgmpdns"
4. Check spreadsheet:
   - Should show single row (8 items < 32)
   - Landing at position 4 (eduppu-1=3, shown as position 4)

5. Change to: Thalam custom, Beats=7, Nadai=2 → cycleLength=14
6. Eduppu=4, phrase="srgmpdns" (8 notes)
7. Calculation:
   - leadingCommas = (4 - 1 - 8) % 14 = (-5) % 14 = 9
   - Full phrase = 9 commas + 8 notes = 17 items total
8. Check spreadsheet:
   - Row 1: 9 commas + first 5 notes (srgmp) = 14 cells (landing marked at position 4)
   - Row 2: remaining 3 notes (dns) = 3 cells
9. Verify landing is only marked on row 1, position 4

### 5. **Cycle Lines with Chromatic Support**
- Each cycle line has its own eduppu and phrase
- Note counting works per-line with variant support
- Each line in spreadsheet renders independently

**Manual Test Steps:**
1. Create song with scale "r2 g2 m1 d2 n2"
2. Add main phrase: "srgmpdns"
3. Add Cycle 1
4. Add Line 1 to Cycle 1: phrase "sr1g2m1"
5. Should show:
   - Note count: 4 notes (sr1 = 1, g2 = 1, m1 = 1)
   - Spreadsheet row with variants applied

## Verification Checklist

- [ ] Scale field appears below Tags in metadata section
- [ ] Scale field saves and loads with song
- [ ] Note counting works with single variants (r1, r2, r3)
- [ ] Spreadsheet shows resolved variants in cells
- [ ] Multi-line wrapping occurs when phrase exceeds cycleLength
- [ ] Landing position (eduppu) only shows on first row
- [ ] Phrase overrides work (e.g., r1 overrides scale default for that note)
- [ ] Cycle lines support chromatic variants
- [ ] Song with chromatic variants can be saved to server
- [ ] Song with chromatic variants can be loaded from server

## Expected Behavior Examples

### Example 1: Simple Scale Resolution
```
Scale: "r2 g2 m1 d2 n2"
Phrase: "rgm"
Result: "r2g2m1" (each swara gets scale variant)
Note Count: 3
```

### Example 2: Partial Override
```
Scale: "r2 g2 m1 d2 n2"
Phrase: "r1gm"
Result: "r1g2m1" (r1 is explicit override, g and m use scale)
Note Count: 3
```

### Example 3: Multi-Line with Misra Thalam
```
Beats: 7 (Misra), Nadai: 2
CycleLength: 14
Eduppu: 4
Phrase: "srgmpdns" (8 notes)
Leading Commas: 9
Row 1: ",,,,,,,,,,srgmp" (14 cells)
Row 2: "dns" (3 cells)
Landing: marked at position 4 of Row 1
```

## Debugging Tips

1. **Check browser console** (F12) for JavaScript errors
2. **Note count not updating**: Verify `updatePhrase()` is called after phrase input
3. **Scale not applying**: Verify scale field is populated and `parseScale()` returns expected map
4. **Multi-line wrapping not working**: Verify cycleLength calculation (beats × nadai)
5. **Landing not showing**: Verify eduppu value matches row position calculation

## Once Validated

After confirming all features work:
1. Note which test cases passed/failed
2. Any edge cases discovered should be documented
3. Ready for git commit with message: "Implement chromatic swara variants and multi-line spreadsheet wrapping"
