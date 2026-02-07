# Kanakku Calculator - Complete Features List

## Overview
A comprehensive web-based Carnatic music phrase timing calculator with MIDI export, raga system, and advanced filtering capabilities.

---

## Core Features

### 1. Phrase Input & Composition
- **Swara Input**: Enter Carnatic music swaras (s, r, g, m, p, d, n)
- **Rests**: Use commas (,) to represent rests/silences in phrases
- **Dotted Characters**: 
  - Dot Above (˙): Raises note by one octave (+12 semitones)
  - Dot Below (̇): Lowers note by one octave (-12 semitones)
  - Support for both precomposed Unicode forms (ṡ, ṙ, etc.) and combining marks
- **Raga Notes System**:
  - Assign chromatic variants to each swara (variants 1, 2, 3)
  - Numbers 1/2/3 select different pitches within each swara
  - Independent from dot modifiers
  - Proper semitone offset mapping per swara

### 2. Timing Calculations
- **Beats**: Set cycle length (3-16 beats supported)
- **Nadai**: Set divisions per beat (3, 4, 5, 7, 9 supported)
- **Eduppu (Starting Position)**: Set where phrase begins in cycle
- **Sruthi (Base Key)**: Choose starting pitch (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
- **Automatic Calculations**:
  - Cycle length = beats × nadai
  - Phrase length (note count)
  - Landing beat position
  - Starting position in cycle

### 3. User Interface Elements
- **Visual Feedback**:
  - Real-time updates as you type
  - Note count display
  - Cycle/phrase information panels
  - Beat and nadai separator visualization
- **Control Buttons**:
  - Add Dot Above/Below
  - Undo/Redo (with full history)
  - Clear Pattern
  - Format Text
  - Reset All
  - Export/Save options

---

## Audio Features

### 4. Audio Playback
- **Web Audio API Integration**:
  - Real-time sine wave synthesis
  - Proper frequency calculation based on MIDI note values
  - Velocity-based amplitude variation
  - Support for rests (velocity = 0)
- **Tempo Control**:
  - BPM selection (configurable)
  - Tempo-based note duration calculation
- **Playback Synchronization**:
  - Matches staff/MIDI layout
  - Includes leading rests per starting position
  - Proper nadai-based timing

---

## MIDI Export Features

### 5. MIDI File Generation
- **MIDI Creation**:
  - Custom MIDI binary generation (no external libraries)
  - Proper MIDI header (MThd) and track (MTrk) chunks
  - 480 ticks per quarter note resolution
  - Configurable tempo via BPM
- **Note Data**:
  - Each note calculated with proper MIDI pitch
  - Sruthi-based transposition
  - Chromatic variant support
  - Octave adjustments via dot modifiers
  - Rests represented as velocity=0 notes
- **File Persistence**:
  - MIDI files saved server-side in `midi_files/` directory
  - Persistent through kanakku save/load
  - Base64 encoding for data storage

### 6. MIDI Visualization
- **Staff Display**:
  - SVG-based treble clef staff (5 lines)
  - Visual note representation with stems
  - Beat/nadai grouping indicators
  - Metadata display (Sruthi, BPM, Beats, Nadai)

### 7. MuseScore Integration
- **Open in MuseScore Button**:
  - Directly open MIDI files in MuseScore desktop application
  - Server-side file path handling
  - Cross-platform support (Windows, Mac, Linux)

### 8. Text Export
- **Export Format**:
  - Cycle-based layout with separators
  - Beat markers (single |) between nadai groups
  - Cycle markers (||) at end of each cycle
  - Includes leading commas based on starting position
  - Preserves all character information (swaras, dots, numbers, rests)
  - CSV-compatible format

---

## Data Management

### 9. Save & Load System
- **Persistent Storage**:
  - JSON-based `kanakku.json` file
  - Server-side persistence via Flask
  - RESTful API endpoints (`/api/kanakkus`)
- **Saved Kanakku Data**:
  - Name, phrase, beats, nadai, eduppu
  - Sruthi, raga notes configuration
  - Tags (comma-separated)
  - MIDI file path and data
  - Unique ID for tracking
- **Load Operations**:
  - Auto-populate all fields from saved entry
  - Restore audio and MIDI configurations
  - MIDI staff auto-displays for saved kanakkus

### 10. Filtering & Search
- **Tag System**:
  - Add tags when saving kanakkus (e.g., "varnam, palavi, short")
  - Search/filter by tags
  - Multiple tags supported
- **Dynamic Filters**:
  - **Text Search**: Search by name or phrase content
  - **Beats Filter**: Filter by exact beat count
  - **Nadai Filter**: Filter by exact nadai value
  - **Tag Filter**: Match any tag in the kanakku
  - **Clear Filters**: Reset all filters with one click
- **Real-Time Results**:
  - Filters apply instantly as you type
  - Combine multiple filters for precise results
  - Maintains full list visibility

### 11. Sidebar Navigation
- **Alphabetical Grouping**: Kanakkus grouped by first letter
- **Quick Index**: Click letters to jump to groups
- **Organized Display**: Beats and nadai info shown inline
- **Interactive Items**: Click kanakku to load, buttons to delete/open MIDI

---

## Raga System

### 12. Chromatic Variant System
- **Raga Notes Input**:
  - Format: swara+number (e.g., r1, r2, r3, g2, m1)
  - Separated by commas and spaces
- **Variant Offsets** (semitone adjustments):
  - **Ri (r)**: [1: -1, 2: 0, 3: +1] (C#, D, D#)
  - **Ga (g)**: [1: -2, 2: -1, 3: 0] (B, C, C#)
  - **Ma (m)**: [1: -1, 2: 0, 3: +1] (D#, E, F)
  - **Pa (p)**: [1: -1, 2: 0, 3: +1] (G#, A, A#)
  - **Dha (d)**: [1: -2, 2: -1, 3: 0] (G, G#, A)
  - **Ni (n)**: [1: -2, 2: -1, 3: 0] (A#, B, C#)
- **Application**:
  - Chromatic variants independent from dot modifiers
  - Variants affect both audio playback and MIDI output
  - Proper tuning for ragas with variant swaras

---

## Advanced Features

### 13. Undo/Redo System
- **Full History Tracking**:
  - Every phrase modification tracked
  - Navigate history with Undo/Redo buttons
  - Keyboard shortcuts (Ctrl+Z, Ctrl+Y)
  - Visual button enable/disable states

### 14. Pattern Validation
- **Check Pattern Feature**:
  - Analyze phrase patterns
  - Identify repeating sequences
  - Count pattern occurrences
  - Display summary statistics

### 15. Responsive Design
- **Flexible Layout**:
  - Resizable sidebar (drag splitter)
  - Mobile-friendly interface
  - Collapsible sections
  - Accessible button arrangements

---

## Technical Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Backend** | Flask (Python) |
| **Audio** | Web Audio API |
| **MIDI** | Custom binary generation (no external libs) |
| **Data** | JSON persistence |
| **Storage** | Server-side file system |
| **Visualization** | SVG (staff notation) |

---

## File Structure

```
Kanakku.html          - Main HTML/CSS/JavaScript file (2463+ lines)
app.py                - Flask backend (442+ lines)
kanakku.json          - Persisted kanakku entries
midi_files/           - Generated MIDI files directory
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main HTML page |
| `/api/kanakkus` | GET | Retrieve all saved kanakkus |
| `/api/kanakkus` | POST | Create new kanakku |
| `/api/kanakkus/{id}` | PUT | Update existing kanakku |
| `/api/kanakkus/{id}` | DELETE | Delete kanakku |
| `/api/open-midi` | POST | Open MIDI file in MuseScore |

---

## Version History

### Latest (Feb 7, 2026)
✅ Complete filtering system with tags, beats, nadai
✅ Text export with leading commas based on starting position
✅ Raga chromatic variant system (fully functional)
✅ MIDI persistence and MuseScore integration
✅ Comprehensive save/load with all parameters
✅ Undo/Redo with full history
✅ Audio playback with proper frequency calculation
✅ Pattern validation and analysis

---

## Summary

The Kanakku Calculator is a feature-rich tool for Carnatic music practitioners to:
- Compose and analyze timed phrases
- Generate MIDI representations for notation software
- Store and organize collections with filtering
- Practice with audio playback
- Export in multiple formats
- Explore raga systems with chromatic variants

All features integrate seamlessly with a clean, accessible interface designed for musicians of all levels.
