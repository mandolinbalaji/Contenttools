# Chromatic Variant Implementation - Test Cases

## Test Case 1: countNotes() Function - Basic Variants
**Setup:** Browser console
**Test Code:**
```javascript
countNotes("srgmpdns")        // Should be 8
countNotes("sr1g2m1d2n2s")    // Should be 8
countNotes("r1g2m1d2n2")      // Should be 5
countNotes("s,rg,,m")         // Should be 5
countNotes("srgmpdns r1g2")   // Should be 10 (space handled correctly)
```

## Test Case 2: parseScale() Function - Scale Parsing  
**Setup:** Browser console
**Test Code:**
```javascript
const scale1 = parseScale("r2 g2 m1 d2 n2")
console.log(scale1)  // {r: 'r2', g: 'g2', m: 'm1', d: 'd2', n: 'n2'}

const scale2 = parseScale("r1g3m2,d1n3")  // Mixed format
console.log(scale2)  // {r: 'r1', g: 'g3', m: 'm2', d: 'd1', n: 'n3'}

const scale3 = parseScale("")
console.log(scale3)  // {} (empty)
```

## Test Case 3: resolvePhrase() Function - Scale Resolution
**Setup:** Browser console
**Test Code:**
```javascript
const scale = parseScale("r2 g2 m1 d2 n2")

// Test default resolution
resolvePhrase("rgm", scale)       // Should be "r2g2m1"

// Test explicit override
resolvePhrase("r1gm", scale)      // Should be "r1g2m1"

// Test fixed notes unaffected
resolvePhrase("srgmpdns", scale)  // Should be "sr2g2m1pd2n2s"

// Test commas preserved
resolvePhrase("s,rg,,m", scale)   // Should be "s,r2g,,m1"
```

## Test Case 4: UI - Scale Field Integration
**Steps:**
1. Open KalpanaSwaramComposer.html
2. Verify scale input appears below Tags section
3. Enter scale "r2 g2 m1 d2 n2"
4. Change to another field (triggers change event)
5. Check browser console: `currentSong.scale` should equal "r2 g2 m1 d2 n2"
6. Refresh page
7. Verify scale field still shows "r2 g2 m1 d2 n2"

## Test Case 5: Spreadsheet - Single Row (No Wrapping)
**Setup:**
- Thalam: Adhi (8 beats), Nadai: 4 → CycleLength = 32
- Eduppu: 4
- Scale: "r2 g2 m1 d2 n2"
- Phrase: "srgmpdns"

**Expected Result:**
- Note count: 8
- Leading commas: (4-1-8) % 32 = -5 % 32 = 27
- Total items: 27 + 8 = 35 items (exceeds 32!)
- Actually this will wrap. Let me recalculate...

Wait, let me recalculate the leading commas formula. With eduppu=4, noteCount=8, cycleLength=32:
- (eduppu - 1 - noteCount) % cycleLength
- = (4 - 1 - 8) % 32  
- = -5 % 32
- In JavaScript, -5 % 32 = -5, so we need to add cycleLength: -5 + 32 = 27

So we have 27 commas + 8 notes = 35 items total.
Row 1: 32 cells (27 commas, then first 5 notes: srgmp)
Row 2: 3 cells (dns)

Let me revise the test:

## Test Case 5: Spreadsheet - Multi-Line Wrapping (Revised)
**Setup:**
- Thalam: Adhi (8 beats), Nadai: 4 → CycleLength = 32
- Eduppu: 4
- Scale: "r2 g2 m1 d2 n2"
- Phrase: "srgmpdns"

**Expected Result:**
- Note count: 8
- Leading commas: 27
- Row 1: 27 commas + "sr2g2m1p" (lands at position 3 = cell 4 when 0-indexed) = 32 cells
- Row 2: "d2n2s" = 5 cells
- Landing marker: Should be on Row 1, column 4 (eduppu value)

**Verification Steps:**
1. Check spreadsheet displays 2 rows for PHRASE line
2. Row 1 label shows "PHRASE"
3. Row 2 label shows "(cont'd)"
4. Landing cell has green background on Row 1, column 4
5. Resolved notes show as "sr2g2m1p" with variants applied

## Test Case 6: Spreadsheet Multi-Line - Simpler Misra Example
**Setup:**
- Beats: 7 (Misra), Nadai: 2 → CycleLength = 14
- Eduppu: 4
- Scale: "r2 g2 m1 d2 n2"
- Phrase: "srgmpdns"

**Calculation:**
- Note count: 8
- Leading commas: (4 - 1 - 8) % 14 = (-5) % 14 = 9
- Row 1: ",,,,,,,,,,srgmp" (9 commas + s,r,g,m,p) = 14 cells, landing at position 4
- Row 2: "d2n2s" (resolved) = 5 cells

**Verification Steps:**
1. Spreadsheet shows exactly 2 rows (14 cells per row)
2. First row has 9 commas (shown as "-") then notes with variants
3. Landing marked at position 4 on first row
4. Second row shows remaining resolved notes

## Test Case 7: Cycle Line - Chromatic Support
**Setup:**
- Song with scale "r2 g2 m1 d2 n2"
- Create Cycle 1
- Add Line 1: phrase "sr1gm"

**Expected:**
- Note count: 4 (sr1 = 1+1 = 2, g = 1 with scale default, m = 1)
  
Wait, that's wrong. sr1 should be:
- s = 1
- r1 = 1 (digit is part of notation)
- Total: 2, not 3

So "sr1gm":
- s = 1
- r1 = 1  
- g = 1
- m = 1
- Total = 4 notes ✓

**Verification:**
1. Line note count shows "4"
2. Spreadsheet cell for line shows resolved "sr1g2m1"

## Test Case 8: Save/Load Persistence
**Setup:**
- Create song with all new features
- Song name: "TestChromatic"
- Scale: "r2 g2 m1 d2 n2"
- Phrase: "sr1gm"
- Cycle 1, Line 1: "rgm"

**Steps:**
1. Click "Save Song" button
2. Verify success message appears
3. Reload page or select different song then reload this one
4. Verify all fields restored:
   - Scale field shows "r2 g2 m1 d2 n2"
   - Main phrase shows "sr1gm"
   - Cycle note counts and spreadsheet correct

## Test Case 9: Override Instance-Specific Behavior
**Setup:**
- Scale: "r2 g2 m1 d2 n2"
- Create 2 cycle lines in same phrase

**Line 1 phrase:** "r1r2r3"
**Line 2 phrase:** "rrr"

**Expected:**
- Line 1: Each r should display as entered (r1, r2, r3)
- Line 2: All r's should resolve to r2 from scale
- Verify each line independently resolves

## Test Case 10: Edge Cases
**Test:** Empty scale
- Scale: "" (empty)
- Phrase: "srgmpdns"
- Expected: All bare notes shown as-is

**Test:** Partial scale definition
- Scale: "r2 d2" (only r and d defined)
- Phrase: "srgmpdns"
- Expected: "sr2g (scale has g in default?) m p d2 n2 s"
  
Actually, let me reconsider. The user said "scale provides default" but only for the swaras that are in the scale. So with scale "r2 d2":
- s = s (no variant, fixed note)
- r = r2 (from scale)
- g = g (no scale definition)
- m = m (no scale definition)
- p = p (fixed note)
- d = d2 (from scale)
- n = n (no scale definition)
- s = s (fixed note)
- Result: "sr2gmPd2ns"

## Acceptance Criteria
- [ ] countNotes correctly counts r1/r2 as 1 note each
- [ ] Scale field saves and loads
- [ ] Scale resolution applies defaults
- [ ] Phrase overrides work for specific notes only
- [ ] Multi-line wrapping works for both main phrase and cycle lines  
- [ ] Landing position shows only on first row
- [ ] All data persists through save/load
- [ ] No JavaScript errors in browser console
