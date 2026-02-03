# Kanakku MIDI Features

## Overview
The Kanakku phrase timing calculator now includes MIDI rendering and visualization capabilities. Users can convert their Carnatic music phrases to MIDI notation and save the MIDI data persistently with their kanakku entries.

## Key Features

### 1. MIDI Rendering
- **Render MIDI Button** (🎹 MIDI): Converts the current phrase to MIDI data
  - Uses the selected Sruthi as the base key
  - Uses the BPM value for tempo
  - Generates MIDI note data for all swaras in the phrase
  - Normalizes Unicode combining marks (dots) to extract base notes

### 2. MIDI Display
- **Open MIDI Button** (📂 MIDI): Displays the rendered MIDI as musical notation
  - Shows a treble clef staff (5 lines)
  - Displays notes as filled circles with stems
  - Shows metadata: Sruthi, BPM, Beats, Nadai
  - SVG-based visualization for browser compatibility

### 3. MIDI Persistence
- MIDI data is stored with each kanakku entry in `kanakku.json`
- When you save a kanakku after rendering MIDI, the MIDI data is persisted
- When you load a saved kanakku with MIDI data, it automatically displays

## Technical Details

### MIDI Note Mapping
- **Sruthi to Base MIDI Pitch**:
  - C = MIDI 60 (Middle C)
  - C# = MIDI 61
  - D = MIDI 62
  - D# = MIDI 63
  - E = MIDI 64
  - F = MIDI 65
  - F# = MIDI 66
  - G = MIDI 67
  - G# = MIDI 68
  - A = MIDI 69
  - A# = MIDI 70
  - B = MIDI 71

### Swara to MIDI Offset
Each swara is mapped to a semitone offset from the base sruthi:
- **S (Sa)**: +0 semitones
- **R (Ri)**: +2 semitones
- **G (Ga)**: +4 semitones
- **M (Ma)**: +5 semitones
- **P (Pa)**: +7 semitones
- **D (Dha)**: +9 semitones
- **N (Ni)**: +11 semitones

This creates the characteristic Indian raga intervals while using standard MIDI format.

### Note Duration Calculation
```
Note Duration = 60 seconds / (BPM × Nadai)
```

For example, with BPM=80 and Nadai=4:
- Duration per note = 60 / (80 × 4) = 0.1875 seconds

### Data Structure

#### MIDI Data Object (stored in kanakku.json)
```json
{
  "notes": [
    {
      "note": 60,
      "startTime": 0,
      "duration": 0.1875,
      "velocity": 100
    },
    ...
  ],
  "bpm": 80,
  "sruthi": "C#",
  "phrase": "srgmp",
  "beats": 8,
  "nadai": 4
}
```

#### Kanakku Object with MIDI
```json
{
  "id": "unique-id",
  "name": "My Phrase",
  "phrase": "srgmp",
  "beats": 8,
  "nadai": 4,
  "eduppu": 1,
  "sruthi": "C#",
  "midiData": { ... }
}
```

## Usage Workflow

### Creating MIDI for a New Phrase

1. **Enter Phrase**: Type in the phrase (e.g., `srgmp`)
2. **Set Parameters**: 
   - Beats: Select from quick-links or input (default: 8 for Adi Thala)
   - Nadai: Select subdivision (default: 4)
   - Sruthi: Select base note (default: C#)
   - BPM: Select tempo (default: 80, range: 60-160)
3. **Render MIDI**: Click the "🎹 MIDI" (Render MIDI) button
   - Notification appears: "MIDI generated! Click Save to persist."
   - MIDI visualization displays below the staff
4. **Save**: Click the Save button to persist both phrase and MIDI data
5. **Load**: Select the saved kanakku from the sidebar to see the MIDI again

### Working with Saved MIDI

1. **Load Kanakku**: Click on a saved kanakku in the sidebar
2. **View MIDI**: If MIDI data exists, it automatically displays
3. **Open MIDI**: Click the "📂 MIDI" (Open MIDI) button to re-display the MIDI visualization
4. **Regenerate MIDI**: 
   - Click "🎹 MIDI" to generate new MIDI (overwrites previous)
   - Click Save to persist the changes

## MIDI Staff Display

The MIDI visualization shows:

### Staff Elements
- **5 Horizontal Lines**: Standard treble clef staff
- **Treble Clef Symbol** (𝄞): On the left side
- **Note Heads**: Black circles representing note positions
- **Stems**: Vertical lines extending from note heads
- **Metadata**: Sruthi, BPM, Beats, and Nadai information

### Note Positioning
Notes are positioned vertically based on their MIDI pitch:
- **E4 (MIDI 71)**: Center reference point
- **Higher MIDI numbers**: Move upward
- **Lower MIDI numbers**: Move downward
- **Spacing**: Each semitone = half a line spacing on the staff

## Limitations & Notes

1. **Staff Notation Only**: Current visualization is simplified SVG staff notation, not full MuseScore-level rendering
2. **Swara Recognition**: Only recognizes swaras (s, r, g, m, p, d, n) in the phrase
3. **Unicode Handling**: Dot marks (˙, ˚) are automatically normalized and removed from note recognition
4. **No MIDI File Export**: Currently doesn't generate downloadable .mid files
5. **Linear Timing**: All notes have equal duration based on nadai subdivision

## Future Enhancements

Potential improvements for future versions:
- [ ] Export as .mid file format for use in DAWs
- [ ] Import MIDI files and convert back to Kanakku notation
- [ ] Support for ornaments (slides, bends, trills)
- [ ] Different note durations based on eduppu patterns
- [ ] Integration with Verovio or similar for advanced music notation
- [ ] MIDI playback with synthesized swaras
- [ ] Support for multiple sruthi keys in one phrase
- [ ] Custom swara-to-MIDI pitch mapping

## Integration with Flask Backend

### API Endpoints Used
- **POST /api/kanakkus**: Create new kanakku with midiData
- **PUT /api/kanakkus/<id>**: Update kanakku including midiData
- **GET /api/kanakkus**: Load all kanakkus with midiData

### Data Flow
1. Frontend generates MIDI data object from phrase parameters
2. MIDI data stored in `currentMidiData` global variable
3. When user saves, MIDI data included in kanakku object
4. Backend stores in kanakku.json
5. On load, MIDI data retrieved from JSON and displayed

## Troubleshooting

### MIDI doesn't display after rendering
- Ensure you have a valid phrase entered
- Check that Sruthi selection is not empty
- Check browser console for error messages

### "No MIDI data available" message
- The current phrase hasn't been rendered to MIDI yet
- Click the "🎹 MIDI" (Render MIDI) button first
- Or load a saved kanakku that has MIDI data

### MIDI data lost after save
- Make sure to click "🎹 MIDI" to render MIDI **before** clicking Save
- Check that no errors occurred during save (look for alerts)

### Wrong note positions on staff
- Verify the Sruthi selection matches your intended key
- Remember that Sruthi defines only the base pitch, not the scale

## Examples

### Example 1: Simple Sa-Ri-Ga
- Phrase: `s r g`
- Beats: 8 (Adi Thala)
- Nadai: 4
- Sruthi: C#
- BPM: 80
- Result: 3 eighth notes starting from C# (MIDI 61), moving up through D# (63) and E# (65)

### Example 2: Full Scale
- Phrase: `srgmpdns`
- Beats: 8
- Nadai: 4
- Sruthi: A
- BPM: 120
- Result: 8 sixteenth notes spanning an octave starting from A4

### Example 3: Complex Pattern
- Phrase: `s r g m p d n s`
- Beats: 8
- Nadai: 4
- Sruthi: C
- BPM: 100
- Result: Full ascending scale in C with quarter-note tempo

## See Also
- [Kanakku.html](Kanakku.html) - Main application
- [app.py](app.py) - Flask backend
- [kanakku.json](kanakku.json) - Data storage
