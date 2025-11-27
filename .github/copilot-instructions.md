# Copilot Instructions for AnytuneToLRC

## Project Architecture

This is a browser-based HTML/JavaScript tool that converts Anytune `.atcfg` files to LRC (lyrics) format with embedded lyrics processing. The architecture is client-side only:

1. **Dual File Upload Layer**: Handles separate loading of `.atcfg` and `.txt` lyrics files
2. **Lyrics Parser Layer**: Processes lyrics files with tag-based format (PL1:, AL1:, etc.)
3. **Text Processing Layer**: Applies normalization (lowercase, remove special characters)
4. **JSON Modification Layer**: Replaces tag occurrences in .atcfg JSON structure with actual lyrics text
5. **Converter Layer**: Generates LRC from modified .atcfg with embedded lyrics
6. **Output Layer**: Displays editable LRC with separate download options for both modified .atcfg and LRC files

Key design decision: Pure client-side implementation - no server, no build process, no dependencies. Single HTML file with embedded CSS and JavaScript.

## File Structure

```
index.html              # Complete converter (HTML + CSS + JS)
edit-notes.html         # Notation editor with dot accent transformations
*.atcfg                 # Example Anytune config files
*.lrc                   # Example LRC output files
*.txt                   # Example lyrics files with PL1:, AL1: tags
anytune_to_lrc.py       # Legacy Python version (not actively used)
tests/                  # Python tests (legacy)
```

**Important**: The active converter is `index.html` - a standalone HTML file with no external dependencies. Can be opened directly in any browser.

## Development Workflow

### Running the tool
Simply open `index.html` in any modern browser. No build step, no server needed.

### Testing
Manual testing with real `.atcfg` files:
1. Open `index.html` in browser
2. Drag/drop or select `.atcfg` file
3. Verify metadata extraction and timestamp formatting
4. Test copy/download functionality

Use browser DevTools console for debugging.

### Code style
- **Pure vanilla JavaScript** - no frameworks, no build tools
- **Single-file architecture** - all HTML, CSS, JS in one file for portability
- **Responsive design** - works on mobile and desktop
- **JSDoc comments** for complex functions

## Project-Specific Patterns

### .atcfg File Structure
`.atcfg` files are JSON with this hierarchy:
```javascript
data.trackData[0].audioMarks[].time  // Array of timing markers in seconds
data.trackData[0].title              // Song title
data.trackData[0].artist             // Artist name  
data.trackData[0].albumTitle         // Album name (note: not 'album'!)
```

### LRC Timestamp Formatting
JavaScript implementation in `formatTimestamp()`:
```javascript
const minutes = Math.floor(seconds / 60);
const secs = seconds % 60;
const mm = String(minutes).padStart(2, '0');
const ss = secs.toFixed(2).padStart(5, '0');  // 2 decimal places
return `[${mm}:${ss}]`;
```
Example: `82.922743764172338` → `[01:22.92]`

### Marker Sorting
Always sort `audioMarks` by `time` before generating LRC:
```javascript
audioMarks.sort((a, b) => a.time - b.time);
```

### Lyrics File Processing
Lyrics files use tag-based format with colon separators:
```javascript
// Input format: "PL1: bantu riti koluviya vayya rama"
// Output: lowercase + special chars removed → "bantu riti koluviya vayya rama"
const normalizedLyrics = lyrics.toLowerCase().replace(/[^a-z0-9\s]/g, '');
```

### Tag Replacement Logic
Lyrics tags are replaced in the .atcfg JSON structure with actual lyrics text:
```javascript
// Function replaces tags in audioMarks with lyrics
function replaceTagsInAtcfg(audioMarks, lyricsMap) {
    audioMarks.forEach((mark, index) => {
        const possibleTags = [
            `PL${index + 1}`,  // PL1, PL2, PL3...
            `AL${index + 1}`,  // AL1, AL2, AL3...
            `L${index + 1}`,   // L1, L2, L3...
            `${index + 1}`,    // 1, 2, 3...
        ];

        for (const tag of possibleTags) {
            if (lyricsMap[tag]) {
                mark.lyrics = lyricsMap[tag];  // Embed lyrics in JSON
                break;
            }
        }
    });
}
```

## Integration Points

- **Input**: `.atcfg` files (Anytune config files) - JSON format only
- **Lyrics**: `.txt` files with tag-based format (PL1:, AL1:, etc.) - required for lyrics embedding
- **Output**: 
  - Modified `.atcfg` files with embedded lyrics (JSON format)
  - Standard LRC files (.lrc) with UTF-8 encoding
- **Metadata**: Extracts `title`, `artist`, `albumTitle` from `trackData[0]`
- **Browser APIs**: FileReader (file loading), Clipboard API (copy), Blob/URL (download)

## Common Tasks

### Adding metadata field support
Update the `processAtcfgData()` function to extract new fields:
```javascript
const bpm = trackData.bpm || '';
if (bpm) lrc += `[bpm:${bpm}]\n`;
```

### Changing LRC timestamp precision
Modify `formatTimestamp()` function:
```javascript
const ss = secs.toFixed(2).padStart(5, '0');  // Change .toFixed(2) to .toFixed(3) for milliseconds
```

### Adding text to markers
Currently generates empty markers. To add text/lyrics:
1. Check if `.atcfg` has text fields in `audioMarks` objects
2. Modify `generateLrcContent()` to append text:
```javascript
const text = mark.text || mark.label || '';
lrc += `${timestamp}${text}\n`;
```

### Styling changes
All CSS is in `<style>` block. Key classes:
- `.upload-area` - drag/drop zone styling
- `.info-section` - metadata display
- `.output-area` - LRC preview with textarea
