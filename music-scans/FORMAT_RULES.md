# Kanakku Format Rules

## Notation System

### Base Swaras (7-note scale)
- s, r, g, m, p, d, n = swaras in lowercase

### Uppercase Conversion
Uppercase swaras convert to lowercase with a following comma:
- S → s,
- R → r,
- G → g,
- M → m,
- P → p,
- D → d,
- N → n,

### Dotted Variants (Microtonality)
Both precomposed and combining mark approaches are supported:
- Dots Above: ṡ, ṙ, ġ, ṁ, ṗ, ḋ, ṅ
- Dots Below: ṣ, ṛ,  g̣, ṃ, p̣,ḍ, ṇ
- Combining Mark: \u0323 (e.g., g + \u0323 = g̣)

### Punctuation
- Semicolon (;) → Double Comma (,,)
  - Example: r;g converts to r,,g
- Commas (,) → Rest/Empty Position
  - Preserved as-is in notation

### Chromatic Variant References (Numbers as Variant Selectors)
For **r, g, m, d, n only**: Numeric characters (1-3) select chromatic variants that affect MIDI playback:
- **r1, r2, r3** = Ri variant 1/2/3 (different pitches for the same raga note)
- **g1, g2, g3** = Ga variant 1/2/3
- **m1, m2** = Ma variant 1/2
- **d1, d2, d3** = Dha variant 1/2/3  
- **n1, n2, n3** = Ni variant 1/2/3

Example in C sruthi: r1 plays C#, r2 plays D, r3 plays D# (different pitches, same raga note role)

**Special Rule for Sa and Pa**: These notes have NO variants. If followed by numbers, the numbers are ignored:
- **s1, s2, s3** → treated as just **s** (numbers stripped)
- **p1, p2, p3** → treated as just **p** (numbers stripped)

**Important**: "n3" occupies **1 note position** on the staff, not 2. The "3" is a chromatic variant selector (affects which pitch is played in MIDI, but takes 1 staff position).

### MIDI Format Conversion Rule
When 's' or 'p' (in any form: s, ṡ, ṣ, ṣ, p, ṗ, p̣) is followed by a number (1-9), convert ignore the number:
- ṡ1 → ṡ (dotted s with MIDI pitch 1 becomes base ṡ)
- ṗ2 → ṗ (dotted p with MIDI pitch 2 becomes base ṗ)
- ṣ3 → ṣ (dotted s below with MIDI pitch 3 becomes base ṣ)
- p̣1 → p̣ (dotted p below with MIDI pitch 1 becomes base p̣)

This ensures consistent MIDI notation where only base swaras carry pitch information.

### Valid Input Examples
- `ġṙṡndṙṡndpṡndpm` = 15 notes, occupies 15 positions
- `ġṙṡndṙṡn3dpṡndpm` = 15 notes (count excludes MIDI data), occupies 15 positions on staff
- `r1r2r3g1g2g3m1m2d1d2d3n1n2n3` = 14 notes (count excludes MIDI data), occupies 14 positions on staff

### Format Button Behavior
The format button applies these rules:
1. Uppercase letters → lowercase + comma
2. Semicolons → double commas
3. Removes pipes (|) and spaces (these are noise)
4. Preserves valid swaras, commas, dotted variants, and MIDI references
5. Converts output to lowercase
6. Updates history (with undo/redo support)

### Example Format Transformations
| Input | Output | Position Count |
|-------|--------|-----------------|
| S | s, | 2 |
| R;G | r,,g, | 5 |
| r1r2 | r1r2 | 2 |
| n 3 d p | n3dp | 3 |
| sr\|gm | srgm | 4 |
| S;R;G | s,,r,,g, | 8 |
