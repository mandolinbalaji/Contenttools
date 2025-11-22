# Copilot Instructions for AnytuneToLRC

## Project Architecture

This is a browser-based HTML/JavaScript tool that converts Anytune `.atcfg` files to LRC (lyrics) format. The architecture is client-side only:

1. **File Upload Layer**: Handles drag-and-drop and file selection with validation
2. **Parser Layer**: JavaScript JSON parsing of `.atcfg` structure
3. **Converter Layer**: Extracts `time` values from `audioMarks` array and formats to LRC
4. **Output Layer**: Displays editable LRC with copy/download functionality

Key design decision: Pure client-side implementation - no server, no build process, no dependencies. Single HTML file with embedded CSS and JavaScript.

## File Structure

```
index.html              # Complete converter (HTML + CSS + JS)
*.atcfg                 # Example Anytune config files
*.lrc                   # Example LRC output files
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

### File Handling
Use `FileReader.readAsText()` to load `.atcfg` files client-side:
```javascript
const reader = new FileReader();
reader.onload = (e) => {
    const data = JSON.parse(e.target.result);
    // process data
};
reader.readAsText(file);
```

## Integration Points

- **Input**: `.atcfg` files (Anytune config files) - JSON format only
- **Output**: Standard LRC files (.lrc) with UTF-8 encoding
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
