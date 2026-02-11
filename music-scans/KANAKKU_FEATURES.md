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
- **Raga Notes System** (Chromatic Variants):
  - Only **Ri (r), Ga (g), Dha (d), Ni (n)** have chromatic variants (1, 2, 3)
  - **Sa (s) and Pa (p)** are fixed pitches with no variants
  - Numbers 1/2/3 select different chromatic pitches (e.g., r1=C#, r2=D, r3=D# in C sruthi)
  - MIDI playback uses the variant pitch (not base note)
  - Independent from dot modifiers
  - Proper semitone offset mapping per swara and variant

### 2. Pattern Generator
- **Quick Pattern Input**:
  - Enter digit pattern in "Pattern Input" field (e.g., "51515")
  - Each digit represents a group size that generates a numeric sequence
  - Auto-generates phrase using numbers 1-9 as placeholder content
- **How It Works**:
  - Pattern "51515" generates phrase "12345112345112345"
  - Pattern "535" generates phrase "12345123545"
  - Each digit cycles through 1-9 sequence, repeating as needed
  - Numbers in the phrase represent musical content positions
- **Numbers as Phrase Content**:
  - When generated from pattern input, numbers (0-9) are treated as valid phrase content
  - Display in staff cells just like swara characters
  - Can be combined with grouping colors for visual organization
  - Useful for timing and phrase analysis without specific swara assignments
- **Integration with Grouping**:
  - Pattern-generated numeric phrases work seamlessly with grouping colors
  - Example: Pattern "51515" with Grouping "51515" creates matching color groups
  - Each group gets a unique pastel color for visual distinction
- **Check Pattern Button**:
  - Validates the pattern input format
  - Auto-fills the phrase field with generated numeric sequence
  - Updates note count and all timing calculations
  - Triggers staff recalculation

### 2B. Kalpana Swara (Multiple Variations)
**Purpose**: Create different melodic variations of a phrase that all land at the same eduppu position (landing beat) within a cycle.

- **Multiple Variation Support**:
  - Add multiple Kalpana lines using "+ Add Line" button
  - Each variation is labeled (Kalpana 1, Kalpana 2, Kalpana 3, etc.)
  - Each variation independently lands at the eduppu position
  - Display as separate labeled staff sections below main phrase (compact layout)

- **Landing Position Calculation**:
  - **Target**: All Kalpana lines must land at position = Eduppu - 1
  - **Formula**: `leading_commas = (eduppu - 1 - note_count) mod cycle_length`
  - Example (Beats=7, Nadai=4, Cycle=28, Eduppu=4):
    - Target landing = position 3 (4-1)
    - 12-note phrase → add 19 commas to land at position 3 → (3-12) mod 28 = 19
    - 24-note phrase → add 8 commas to land at position 3 → (3-24) mod 28 = 8
  - Leading commas automatically calculated and prepended when user enters phrase

- **Staff Display**:
  - Main phrase in primary section
  - Each Kalpana variation in separate mini staff section with label
  - Compact layout: no wasted space
  - Star marker (*) shows eduppu position for each line
  - All variations share same beat/nadai/cycle structure

- **Data Persistence**:
  - Multiple Kalpana variations stored in kanakku.json
  - Structure: `kalpanas: [{ label: "Kalpana 1", phrase: "...", eduppu: 4 }, ...]`

- **Export & MIDI**:
  - Text export includes all variations labeled with their line numbers
  - MIDI file includes all variations as separate tracks or sequential notation
  - Each variation respects its own calculated landing position

### 3. Timing Calculations
- **Beats**: Set cycle length (3-16 beats supported)
- **Nadai**: Set divisions per beat (3, 4, 5, 7, 9 supported)
- **Eduppu (Starting Position)**: Set where phrase begins in cycle
- **Sruthi (Base Key)**: Choose starting pitch (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
- **Automatic Calculations**:
  - Cycle length = beats × nadai
  - Phrase length (note count)
  - Landing beat position
  - Starting position in cycle

### 4. User Interface Elements
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

### 5. Audio Playback
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

### 6. MIDI File Generation
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

### 7. MIDI Visualization
- **Staff Display**:
  - SVG-based treble clef staff (5 lines)
  - Visual note representation with stems
  - Beat/nadai grouping indicators
  - Metadata display (Sruthi, BPM, Beats, Nadai)

### 8. MuseScore Integration
- **Open in MuseScore Button**:
  - Directly open MIDI files in MuseScore desktop application
  - Server-side file path handling
  - Cross-platform support (Windows, Mac, Linux)

### 9. Text Export
- **Export Format**:
  - Cycle-based layout with separators
  - Beat markers (single |) between nadai groups
  - Cycle markers (||) at end of each cycle
  - Includes leading commas based on starting position
  - Preserves all character information (swaras, dots, numbers, rests)
  - CSV-compatible format

---

## Data Management

### 10. Save & Load System
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

### 11. Filtering & Search
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

### 12. Sidebar Navigation
- **Alphabetical Grouping**: Kanakkus grouped by first letter
- **Quick Index**: Click letters to jump to groups
- **Organized Display**: Beats and nadai info shown inline
- **Interactive Items**: Click kanakku to load, buttons to delete/open MIDI

---

## Raga System

### 13. Chromatic Variant System
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

## Rules & Conventions

### Pattern Generator Rules
1. **Valid Pattern Input**:
   - Only digits 0-9 are accepted in pattern field
   - Non-digit characters are ignored
   - Empty or invalid patterns trigger an alert
   - Each digit must be 0-9 (no multi-digit numbers)

2. **Phrase Generation Rules**:
   - Digit value determines group size
   - Example: "5" creates group of 5: "12345"
   - Zero ("0") is used as valid digit, creates no output for that group
   - Pattern is processed sequentially left to right
   - Numeric sequence cycles through 1-9 and restarts

3. **Generated Phrase Format**:
   - Output consists only of numeric characters (1-9)
   - Numbers represent timing positions
   - No swaras, dots, or special characters in output
   - Result is stored in the main Phrase field
   - Example pattern "51515" → phrase "12345112345112345"

4. **Integration with Grouping**:
   - Grouping field accepts same digit patterns as pattern input
   - Grouping "51515" creates 5 color groups of sizes: 5, 1, 5, 1, 5
   - Each group receives a unique pastel color
   - Colors overlay/replace default background colors
   - Color array: Red, Blue, Green, Orange, Purple, Pink, Cyan, Yellow (repeats if needed)

5. **Number Handling in Phrases**:
   - **When from pattern**: Numbers are the phrase content itself
   - **When manual entry**: Numbers (1-3) after swaras are MIDI octave variants
   - System distinguishes between the two contexts automatically
   - MIDI variant numbers only append to swara characters, not standalone numerics

6. **Display Rules**:
   - All valid phrase content displays in staff cells
   - Numbers from pattern display in subdivision-char div
   - Staff background colors:
     - Green (#e8f5e9) = first note position
     - Red (#ffebee) = landing/eduppu position
     - Light gray (#f5f5f5) = intermediate notes
     - Custom pastel colors = grouping overlay
   - Numbers are centered and monospace-styled

7. **Calculation Impact**:
   - Pattern-generated phrases trigger full recalculation
   - Phrase length (note count) updates automatically
   - Starting position and landing beat computed normally
   - Timing calculations same as manually-entered phrases
   - MIDI export treats numeric content as regular notes

### General Phrase Rules
- **Valid Characters**: s, r, g, m, p, d, n, (uppercase variants), commas (rests), dots above/below, numbers (0-9)
- **Swara Character Requirements**: Uppercase variants (S, R, G, M, P, D, N) work identically to lowercase
- **Dot Modifiers**: Can combine with any swara; independent from numeric variants
- **Rest Representation**: Single comma (,) represents one rest position
- **Character Order**: Swaras first, then optional numeric variant (1-3), then optional dots

---

## Advanced Features

### 14. Undo/Redo System
- **Full History Tracking**:
  - Every phrase modification tracked
  - Navigate history with Undo/Redo buttons
  - Keyboard shortcuts (Ctrl+Z, Ctrl+Y)
  - Visual button enable/disable states

### 15. Pattern Validation
- **Check Pattern Feature**:
  - Analyze phrase patterns
  - Identify repeating sequences
  - Count pattern occurrences
  - Display summary statistics

### 16. Responsive Design
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
