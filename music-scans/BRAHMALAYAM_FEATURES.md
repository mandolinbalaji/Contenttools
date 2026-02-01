# BrahmaLayam - Carnatic Notation Editor
## Golden Rules Implementation Status

### ✅ IMPLEMENTED FEATURES

#### 1. **Atomic Notes System** (Golden Rule #1)
- Every note is stored as an object: `{ char: 'S', octave: 0, speed: 1 }`
- Not raw text - ensures proper ^ line and Western Staff sync
- Supported notes: S (Sa), R (Ri), G (Ga), M (Ma), P (Pa), D (Da), N (Ni)
- Octave control: ↑ (up), ↓ (down), no modifier (default)
- Speed control: ^ (double speed), normal speed (1x)

#### 2. **Laya Calculation** (Golden Rule #2)
- Formula: `Total Pulses = Σ(1/speed)` for each note
- Visual display: Shows running pulse count and next Jathi line
- Vertical lines drawn automatically when cumulative pulses reach Jathi value
- Red separator lines (|) indicate Jathi boundaries
- Jathi options: 3 (Tisra), 4 (Chatusra), 5 (Kanda), 7 (Misra), 9 (Sankirna)

#### 3. **Sruthi Mapping** (Golden Rule #3)
- Map 'S' to user-selected Sruthi frequency with Carnatic ratio table
- Standard Carnatic frequency ratios:
  - S: 1.0 (Sa)
  - R: 1.067 (Ri, 16/15)
  - G: 1.125 (Ga, 9/8)
  - M: 1.2 (Ma, 6/5)
  - P: 1.333 (Pa, 4/3)
  - D: 1.5 (Da, 3/2)
  - N: 1.6875 (Ni, 27/16)
- Sruthi choices: C (261.63 Hz), D, E, F, G
- Octave support: Notes can be transposed up/down by 2x frequency

#### 4. **Real-time Visualization**
- **Carnatic Notation Panel**: Shows notes with octave indicators (↑↓) and speed (.)
- **Vertical Jathi Lines**: Red separators appear automatically after Jathi count
- **Western Staff Preview**: Live VexFlow rendering with octave-aware note mapping
- **Note Count**: Accurate count of valid notes only

#### 5. **Audio Playback**
- Play individual notes with Tone.js synthesis
- Speed-aware playback: Fast notes (2x speed) play for half duration
- BPM control: Adjustable tempo (30-300 BPM)
- Octave-aware frequency generation
- Responsive synthesis with attack/decay envelope

#### 6. **Lesson Management**
- Create new lessons with auto-generated IDs
- Load lessons from library sidebar
- Save lessons with metadata (Thala, Jathi, Sruthi, BPM, total pulses)
- Delete lessons
- Stores both raw text AND atomic notes structure

#### 7. **Backend API Endpoints** (Golden Rule #4 & #5)
- **GET /api/lessons**: Returns list of filenames from lessons/ folder
- **POST /api/save**: Writes JSON object to /data/ folder
- **POST /api/export**: Converts JSON to MusicXML format for MuseScore compatibility
- All endpoints support proper error handling

#### 8. **MusicXML Export**
- Converts Carnatic notation to standard music notation format
- Compatible with MuseScore and other notation software
- Exports octave-aware Western note pitches
- Downloads as .musicxml file
- Preserves rhythm information (speed doubles = 8th notes)

### 📊 FEATURE CHECKLIST

| Feature | Status | Notes |
|---------|--------|-------|
| Atomic Notes { char, octave, speed } | ✅ | Fully implemented |
| Note Count (valid notes only) | ✅ | Fixed to not count empty strings |
| Laya Pulse Calculation | ✅ | Σ(1/speed) working |
| Vertical Jathi Lines | ✅ | Red separators appear correctly |
| Carnatic-Western Staff Sync | ✅ | VexFlow with octave mapping |
| Sruthi Mapping (frequency table) | ✅ | Standard Carnatic ratios |
| Thala Support | ✅ | Adi (8), Rupaka (3), Khanda (5), Misra (7) |
| Jathi Visualization | ✅ | Pulse-based, not note-based |
| Audio Playback | ✅ | Tone.js with speed/octave support |
| BPM Control | ✅ | 30-300 range |
| Lesson CRUD | ✅ | Create, Read, Update, Delete |
| Backend /data/ folder | ✅ | POST /api/save support |
| MusicXML Export | ✅ | POST /api/export for MuseScore |
| Mobile Responsive | ✅ | Sidebar/main layout adapts |

### 🎯 USAGE EXAMPLE

1. **Input**: Type `S R G M P` in Carnatic Notes textarea
2. **Parsing**: Converted to atomic notes `[{char:'S', octave:0, speed:1}, {char:'R', ...}, ...]`
3. **Laya**: Each note = 1 pulse → Total 5 pulses
4. **Visualization**: 
   - Carnatic display: `S R G M P`
   - Pulse count: "Pulses: 5.0 | Jathi: 4 | Next line: 4 pulses"
   - Vertical line appears after 4 notes: `S R G M | P`
5. **Western Staff**: Displays D E F# G A in treble clef
6. **Audio**: Click Play → plays 5 notes at 120 BPM
7. **Export**: Click Export → downloads lesson.musicxml for MuseScore

### 📝 NOTES COUNT VALIDATION

Previously: Counted empty strings from split ❌
Now: Only counts valid Carnatic notes (S R G M P D N) ✅

Example:
- Input: `S  R   G M`
- Old count: 6 (included empty strings)
- New count: 4 (only valid notes)

### 🎼 VERTICAL LINE LOGIC

Based on **cumulative pulse count**, not note count:
- Jathi 4: Line appears every 4 pulses
- Note with speed 2 (fast): Counts as 0.5 pulses
- Example: `S R. G M` (with one fast note) → line after 4.5 pulses total

### 🔄 LAST UPDATED
February 1, 2026 - Golden Rules Implementation Complete
