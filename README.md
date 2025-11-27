# AnytuneToLRC

Convert Anytune practice session files (.atcfg) to LRC (lyrics) format for use in music players and karaoke applications.

## Overview

Anytune is a popular music practice app that allows musicians to add markers and annotations to songs. This tool extracts timing markers from `.atcfg` configuration files and converts them to the standard LRC lyrics format.

## Usage

Simply open `index.html` in your web browser:

1. **Load Anytune file**: Click the left area to select your `.atcfg` file
2. **Load lyrics file (optional)**: Click the right area to select a `.txt` lyrics file
3. The tool will extract timing markers from the `audioMarks` array
4. If a lyrics file is provided, it will match lyrics to timestamps
5. View the generated LRC content with metadata (title, artist, album)
6. Edit the LRC content if needed
7. Copy to clipboard or download the `.lrc` file

**No installation required!** Works completely in the browser using JavaScript.

## Lyrics File Format

The lyrics file should be a `.txt` file with lines in this format:

```
PL1: bantu riti koluviya vayya rama
AL1: tunta vinti vani modalaina
PL2: romanchamanu ghana kanchukamu
AL2: rama namamane vara khadgamivi
```

**Tag patterns supported:**
- `PL1`, `PL2`, `PL3`... (Primary Lyrics)
- `AL1`, `AL2`, `AL3`... (Alternate Lyrics)
- `L1`, `L2`, `L3`... (Generic Lyrics)
- `1`, `2`, `3`... (Numeric only)

**Text processing:**
- All lyrics are converted to lowercase
- Special characters are removed (keeping only letters, numbers, and spaces)

## .atcfg File Structure

Anytune configuration files are JSON files with this structure:

```json
{
  "trackData": [{
    "title": "Song Title",
    "artist": "Artist Name",
    "albumTitle": "Album Name",
    "audioMarks": [
      {"time": 3.44, ...},
      {"time": 7.12, ...},
      {"time": 82.92, ...}
    ]
  }]
}
```

The tool extracts `time` values from the `audioMarks` array and converts them to LRC format.

## LRC Output Format

Generated LRC files include metadata headers and timestamp markers:

```
[ar:Artist Name]
[ti:Song Title]
[al:Album Name]
[by:AnytuneToLRC]

[00:03.44]
[00:07.12]
[01:22.92]
```

## Features

- ✅ Browser-based - no installation needed
- ✅ Drag & drop file upload
- ✅ Automatic metadata extraction (title, artist, album)
- ✅ Editable LRC output before download
- ✅ Copy to clipboard or download as .lrc file
- ✅ Sorts markers by timestamp automatically
