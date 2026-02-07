# Kanakku Note Mapping Reference

## Overview
Complete reference guide for the chromatic variant note mapping system used in the Kanakku calculator. Documents how each swara variant maps to MIDI notes across all 12 sruthi (base key) values.

---

## Swara Offset System

Each swara has a base semitone offset from the sruthi, with chromatic variants providing fine-tuning:

| Swara | Base Offset | Variants | Notes |
|-------|-------------|----------|-------|
| **Sa (s)** | 0 | None | Fixed - always the sruthi base |
| **Ri (r)** | 2 | 1=-1, 2=0, 3=+1 | Three chromatic pitches |
| **Ga (g)** | 4 | 1=-2, 2=-1, 3=0 | Three chromatic pitches |
| **Ma (m)** | 5 | 1=0, 2=+1 | Two common variants |
| **Pa (p)** | 7 | None | Fixed - always 7 semitones from sruthi |
| **Dha (d)** | 9 | 1=-1, 2=0, 3=+1 | Three chromatic pitches |
| **Ni (n)** | 11 | 1=-2, 2=-1, 3=0 | Three chromatic pitches |

---

## Complete Sruthi Mappings

### C Sruthi (Base = C4 / MIDI 60)
```
s:  C4    (60)

r1: C#4   (61)    r2: D4    (62)    r3: D#4   (63)
g1: D4    (62)    g2: D#4   (63)    g3: E4    (64)

m1: F4    (65)    m2: F#4   (66)

p:  G4    (67)

d1: G#4   (68)    d2: A4    (69)    d3: A#4   (70)
n1: A4    (69)    n2: A#4   (70)    n3: B4    (71)
```

### C# Sruthi (Base = C#4 / MIDI 61)
```
s:  C#4   (61)

r1: D4    (62)    r2: D#4   (63)    r3: E4    (64)
g1: D#4   (63)    g2: E4    (64)    g3: F4    (65)

m1: F#4   (66)    m2: G4    (67)

p:  G#4   (68)

d1: A4    (69)    d2: A#4   (70)    d3: B4    (71)
n1: A#4   (70)    n2: B4    (71)    n3: C5    (72)
```

### D Sruthi (Base = D4 / MIDI 62)
```
s:  D4    (62)

r1: D#4   (63)    r2: E4    (64)    r3: F4    (65)
g1: E4    (64)    g2: F4    (65)    g3: F#4   (66)

m1: G4    (67)    m2: G#4   (68)

p:  A4    (69)

d1: A#4   (70)    d2: B4    (71)    d3: C5    (72)
n1: B4    (71)    n2: C5    (72)    n3: C#5   (73)
```

### D# Sruthi (Base = D#4 / MIDI 63)
```
s:  D#4   (63)

r1: E4    (64)    r2: F4    (65)    r3: F#4   (66)
g1: F4    (65)    g2: F#4   (66)    g3: G4    (67)

m1: G#4   (68)    m2: A4    (69)

p:  A#4   (70)

d1: B4    (71)    d2: C5    (72)    d3: C#5   (73)
n1: C5    (72)    n2: C#5   (73)    n3: D5    (74)
```

### E Sruthi (Base = E4 / MIDI 64)
```
s:  E4    (64)

r1: F4    (65)    r2: F#4   (66)    r3: G4    (67)
g1: F#4   (66)    g2: G4    (67)    g3: G#4   (68)

m1: A4    (69)    m2: A#4   (70)

p:  B4    (71)

d1: C5    (72)    d2: C#5   (73)    d3: D5    (74)
n1: C#5   (73)    n2: D5    (74)    n3: D#5   (75)
```

### F Sruthi (Base = F4 / MIDI 65)
```
s:  F4    (65)

r1: F#4   (66)    r2: G4    (67)    r3: G#4   (68)
g1: G4    (67)    g2: G#4   (68)    g3: A4    (69)

m1: A#4   (70)    m2: B4    (71)

p:  C5    (72)

d1: C#5   (73)    d2: D5    (74)    d3: D#5   (75)
n1: D5    (74)    n2: D#5   (75)    n3: E5    (76)
```

### F# Sruthi (Base = F#4 / MIDI 66)
```
s:  F#4   (66)

r1: G4    (67)    r2: G#4   (68)    r3: A4    (69)
g1: G#4   (68)    g2: A4    (69)    g3: A#4   (70)

m1: B4    (71)    m2: C5    (72)

p:  C#5   (73)

d1: D5    (74)    d2: D#5   (75)    d3: E5    (76)
n1: D#5   (75)    n2: E5    (76)    n3: F5    (77)
```

### G Sruthi (Base = G4 / MIDI 67)
```
s:  G4    (67)

r1: G#4   (68)    r2: A4    (69)    r3: A#4   (70)
g1: A4    (69)    g2: A#4   (70)    g3: B4    (71)

m1: C5    (72)    m2: C#5   (73)

p:  D5    (74)

d1: D#5   (75)    d2: E5    (76)    d3: F5    (77)
n1: E5    (76)    n2: F5    (77)    n3: F#5   (78)
```

### G# Sruthi (Base = G#4 / MIDI 68)
```
s:  G#4   (68)

r1: A4    (69)    r2: A#4   (70)    r3: B4    (71)
g1: A#4   (70)    g2: B4    (71)    g3: C5    (72)

m1: C#5   (73)    m2: D5    (74)

p:  D#5   (75)

d1: E5    (76)    d2: F5    (77)    d3: F#5   (78)
n1: F5    (77)    n2: F#5   (78)    n3: G5    (79)
```

### A Sruthi (Base = A4 / MIDI 69)
```
s:  A4    (69)

r1: A#4   (70)    r2: B4    (71)    r3: C5    (72)
g1: B4    (71)    g2: C5    (72)    g3: C#5   (73)

m1: D5    (74)    m2: D#5   (75)

p:  E5    (76)

d1: F5    (77)    d2: F#5   (78)    d3: G5    (79)
n1: F#5   (78)    n2: G5    (79)    n3: G#5   (80)
```

### A# Sruthi (Base = A#4 / MIDI 70)
```
s:  A#4   (70)

r1: B4    (71)    r2: C5    (72)    r3: C#5   (73)
g1: C5    (72)    g2: C#5   (73)    g3: D5    (74)

m1: D#5   (75)    m2: E5    (76)

p:  F5    (77)

d1: F#5   (78)    d2: G5    (79)    d3: G#5   (80)
n1: G5    (79)    n2: G#5   (80)    n3: A5    (81)
```

### B Sruthi (Base = B4 / MIDI 71)
```
s:  B4    (71)

r1: C5    (72)    r2: C#5   (73)    r3: D5    (74)
g1: C#5   (73)    g2: D5    (74)    g3: D#5   (75)

m1: E5    (76)    m2: F5    (77)

p:  F#5   (78)

d1: G5    (79)    d2: G#5   (80)    d3: A5    (81)
n1: G#5   (80)    n2: A5    (81)    n3: A#5   (82)
```

---

## JSON Storage Format for kanakku.json

### Proposed Structure
```json
{
  "id": "unique-kanakku-id",
  "name": "Varnam Name",
  "phrase": "srgm pdns",
  "beats": 8,
  "nadai": 4,
  "eduppu": 5,
  "sruthi": "C#",
  "ragaNotes": "r2 g3 m1 d2 n1",
  "tags": ["varnam", "palavi"],
  "noteMappings": {
    "sruthi": "C#",
    "baseNote": 61,
    "mappings": {
      "s": "C#4",
      "r1": "D4", "r2": "D#4", "r3": "E4",
      "g1": "D#4", "g2": "E4", "g3": "F4",
      "m1": "F#4", "m2": "G4",
      "p": "G#4",
      "d1": "A4", "d2": "A#4", "d3": "B4",
      "n1": "A#4", "n2": "B4", "n3": "C5"
    }
  },
  "midiFilePath": "midi_files/varnam.mid"
}
```

---

## Calculation Formula

To generate a MIDI note for any swara variant:

```
MIDI_NOTE = BASE_NOTE + SWARA_OFFSET + VARIANT_OFFSET + DOT_MODIFIER

Where:
- BASE_NOTE = MIDI value of sruthi (60=C4, 61=C#4, ... 71=B4)
- SWARA_OFFSET = base semitone offset for the swara:
    * s=0, r=2, g=4, m=5, p=7, d=9, n=11
- VARIANT_OFFSET = fine-tuning offset for the specific variant:
    * For r: 1=-1, 2=0, 3=+1
    * For g: 1=-2, 2=-1, 3=0
    * For m: 1=0, 2=+1
    * For d: 1=-1, 2=0, 3=+1
    * For n: 1=-2, 2=-1, 3=0
- DOT_MODIFIER = ±12 semitones per octave modifier
    * Dot above (˙) = +12 semitones
    * Dot below (̇) = -12 semitones
```

### Calculation Examples

**r2 in Sruthi A:**
- BASE_NOTE (A4) = 69
- SWARA_OFFSET (r) = 2
- VARIANT_OFFSET (r2) = 0
- DOT_MODIFIER = 0
- Result: 69 + 2 + 0 + 0 = **71 → B4**

**g1 in Sruthi C# with dot above:**
- BASE_NOTE (C#4) = 61
- SWARA_OFFSET (g) = 4
- VARIANT_OFFSET (g1) = -2
- DOT_MODIFIER (above) = +12
- Result: 61 + 4 - 2 + 12 = **75 → D#5**

**m2 in Sruthi F:**
- BASE_NOTE (F4) = 65
- SWARA_OFFSET (m) = 5
- VARIANT_OFFSET (m2) = +1
- DOT_MODIFIER = 0
- Result: 65 + 5 + 1 + 0 = **71 → B4**

---

## Usage Examples

### Python Backend (app.py)

```python
def get_note_mapping(sruthi, swara, variant=None, octave_mod=0):
    """
    Generate MIDI note for a swara variant.
    
    Args:
        sruthi: Base sruthi (C, C#, D, ... B)
        swara: Swara character (s, r, g, m, p, d, n)
        variant: Variant number (1, 2, 3) - None for fixed swaras
        octave_mod: Octave modifier (-12 for below, 0 for middle, 12 for above)
    
    Returns:
        MIDI note number
    """
    sruthi_map = {
        'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64,
        'F': 65, 'F#': 66, 'G': 67, 'G#': 68, 'A': 69,
        'A#': 70, 'B': 71
    }
    
    swara_offsets = {
        's': 0, 'r': 2, 'g': 4, 'm': 5, 'p': 7, 'd': 9, 'n': 11
    }
    
    variant_offsets = {
        'r': {1: -1, 2: 0, 3: 1},
        'g': {1: -2, 2: -1, 3: 0},
        'm': {1: 0, 2: 1},
        'd': {1: -1, 2: 0, 3: 1},
        'n': {1: -2, 2: -1, 3: 0}
    }
    
    base_note = sruthi_map.get(sruthi, 60)
    swara_offset = swara_offsets.get(swara, 0)
    variant_offset = 0
    
    if variant and swara in variant_offsets:
        variant_offset = variant_offsets[swara].get(variant, 0)
    
    midi_note = base_note + swara_offset + variant_offset + octave_mod
    return midi_note

# Usage
note = get_note_mapping('C#', 'r', 2)  # Returns 63 (D#4)
note_upper = get_note_mapping('A', 'm', 2, 12)  # Returns 87 (F6)
```

### JavaScript Frontend (Kanakku.html)

```javascript
function getSwaraVariantOffset(swara, variant) {
    const swaraVariants = {
        'r': { 1: -1, 2: 0, 3: 1 },
        'g': { 1: -2, 2: -1, 3: 0 },
        'm': { 1: 0, 2: 1 },
        'd': { 1: -1, 2: 0, 3: 1 },
        'n': { 1: -2, 2: -1, 3: 0 }
    };
    
    if (swaraVariants[swara] && swaraVariants[swara][variant]) {
        return swaraVariants[swara][variant];
    }
    return 0;  // No variant or fixed swara
}

function getNoteMIDI(sruthi, swara, variant = null, octaveMod = 0) {
    const sruthiMap = {
        'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64,
        'F': 65, 'F#': 66, 'G': 67, 'G#': 68, 'A': 69,
        'A#': 70, 'B': 71
    };
    
    const swaraOffsets = {
        's': 0, 'r': 2, 'g': 4, 'm': 5, 'p': 7, 'd': 9, 'n': 11
    };
    
    const baseNote = sruthiMap[sruthi] || 60;
    const swaraOffset = swaraOffsets[swara] || 0;
    const variantOffset = variant ? getSwaraVariantOffset(swara, variant) : 0;
    
    return baseNote + swaraOffset + variantOffset + octaveMod;
}

// Usage
const midiNote = getNoteMIDI('C#', 'r', 2);  // Returns 63
const withOctave = getNoteMIDI('A', 'm', 2, 12);  // Returns 87
```

---

## Quick Reference Table

For quick lookups, use this table to find MIDI notes:

| Sruthi | s | r1 | r2 | r3 | g1 | g2 | g3 | m1 | m2 | p | d1 | d2 | d3 | n1 | n2 | n3 |
|--------|---|----|----|----|----|----|----|----|----|---|----|----|----|----|----|----|
| **C** | 60 | 61 | 62 | 63 | 62 | 63 | 64 | 65 | 66 | 67 | 68 | 69 | 70 | 69 | 70 | 71 |
| **C#** | 61 | 62 | 63 | 64 | 63 | 64 | 65 | 66 | 67 | 68 | 69 | 70 | 71 | 70 | 71 | 72 |
| **D** | 62 | 63 | 64 | 65 | 64 | 65 | 66 | 67 | 68 | 69 | 70 | 71 | 72 | 71 | 72 | 73 |
| **D#** | 63 | 64 | 65 | 66 | 65 | 66 | 67 | 68 | 69 | 70 | 71 | 72 | 73 | 72 | 73 | 74 |
| **E** | 64 | 65 | 66 | 67 | 66 | 67 | 68 | 69 | 70 | 71 | 72 | 73 | 74 | 73 | 74 | 75 |
| **F** | 65 | 66 | 67 | 68 | 67 | 68 | 69 | 70 | 71 | 72 | 73 | 74 | 75 | 74 | 75 | 76 |
| **F#** | 66 | 67 | 68 | 69 | 68 | 69 | 70 | 71 | 72 | 73 | 74 | 75 | 76 | 75 | 76 | 77 |
| **G** | 67 | 68 | 69 | 70 | 69 | 70 | 71 | 72 | 73 | 74 | 75 | 76 | 77 | 76 | 77 | 78 |
| **G#** | 68 | 69 | 70 | 71 | 70 | 71 | 72 | 73 | 74 | 75 | 76 | 77 | 78 | 77 | 78 | 79 |
| **A** | 69 | 70 | 71 | 72 | 71 | 72 | 73 | 74 | 75 | 76 | 77 | 78 | 79 | 78 | 79 | 80 |
| **A#** | 70 | 71 | 72 | 73 | 72 | 73 | 74 | 75 | 76 | 77 | 78 | 79 | 80 | 79 | 80 | 81 |
| **B** | 71 | 72 | 73 | 74 | 73 | 74 | 75 | 76 | 77 | 78 | 79 | 80 | 81 | 80 | 81 | 82 |

---

## Reference Notes

- **Sa (s)**: Always the sruthi base - no variants
- **Pa (p)**: Always 7 semitones from sruthi - no variants
- **Ma (m)**: Only has 2 variants (m1, m2) - less common in Carnatic music
- **Others** (r, g, d, n): Have 3 chromatic variants for different raga requirements
- **Octave Modifiers**: Each addition/subtraction of 12 shifts one octave
- **MIDI Range**: Standard piano range is MIDI 21-108; this calculator uses 60-82+ primarily

