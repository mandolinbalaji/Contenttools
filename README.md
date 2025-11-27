# AnytuneToLRC

Convert Anytune practice session files (.atcfg) to LRC (lyrics) format for use in music players and karaoke applications.

## Overview

Anytune is a popular music practice app that allows musicians to add markers and annotations to songs. This tool extracts timing markers from `.atcfg` configuration files, embeds lyrics from text files directly into the JSON structure, and converts them to the standard LRC lyrics format.

## Usage

Simply open `index.html` in your web browser:

1. **Load Anytune file**: Click the left area to select your `.atcfg` file
2. **Load lyrics file**: Click the right area to select a `.txt` lyrics file with tag-based format
3. The tool will:
   - Parse lyrics tags (PL1, AL1, etc.) from the text file
   - Replace tag occurrences in the `.atcfg` JSON structure with actual lyrics text
   - Generate a modified `.atcfg` file with embedded lyrics
   - Convert timing markers to LRC format using the embedded lyrics
4. View the generated LRC content with metadata (title, artist, album)
5. Edit the LRC content if needed
6. Download both the modified `.atcfg` file (with embedded lyrics) and the `.lrc` file

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

## Example Files

- `Adamodi_Galade_Charukesi.atcfg` - Sample Anytune configuration file
- `Adamodi_Galade_Charukesi.lrc` - Expected LRC output
- `sample-lyrics.txt` - Example lyrics file with tag format

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
[file:Adamodi_Galade_Charukesi.atcfg]
[ar:ost]
[ti:Adamodi_Galade_Charukesi]
[al:Charukesi]
[by:AnytuneToLRC]

[00:03.4398639455782312]$bantu riti koluviya vayya rama
[00:07.1202721088435377]$tunta vinti vani modalaina
[01:22.922743764172338]$romanchamanu ghana kanchukamu
```

## Features

- ✅ Browser-based - no installation needed
- ✅ Drag & drop file upload
- ✅ Automatic lyrics tag parsing and embedding in .atcfg JSON
- ✅ Generates modified .atcfg files with embedded lyrics
- ✅ Automatic metadata extraction (title, artist, album)
- ✅ Editable LRC output before download
- ✅ Download both modified .atcfg and .lrc files separately
- ✅ Copy to clipboard functionality
- ✅ Sorts markers by timestamp automatically
