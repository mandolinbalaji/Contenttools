# AnytuneToLRC

Convert Anytune practice session files (.atcfg) to LRC (lyrics) format for use in music players and karaoke applications.

## Overview

Anytune is a popular music practice app that allows musicians to add markers and annotations to songs. This tool extracts timing markers from `.atcfg` configuration files and converts them to the standard LRC lyrics format.

## Usage

Simply open `index.html` in your web browser:

1. Click the upload area or drag & drop your `.atcfg` file
2. The tool will extract timing markers from the `audioMarks` array
3. View the generated LRC content with metadata (title, artist, album)
4. Edit the LRC content if needed
5. Copy to clipboard or download the `.lrc` file

**No installation required!** Works completely in the browser using JavaScript.

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
