# AnytuneToLRC + Balaji's Tools

## 🎵 Balaji's Tools - Music Production Dashboard

A unified dashboard for music production tools, providing easy access to all your audio processing applications.

### Quick Launch
```bash
python launch_dashboard.py
```

**Features:**
- **Precision Audio Player**: Advanced looping audio player with sample-accurate playback
- **YouTube to MP3 Server**: Convert YouTube videos to MP3 with web interface
- **Ultimate Vocal Remover (UVR)**: AI-powered vocal separation tool
- **SongIndex Server**: Music library indexing and search server
- **Format Convert**: AnytuneToLRC converter for practice files
- **Generate Video**: Video generation tools

---

## AnytuneToLRC - Convert Practice Files to LRC

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
## YouTube to MP3

Extract audio from YouTube videos and save as high-quality MP3 files.

### Setup

1. Install required packages:
   ```bash
   pip install flask flask-cors yt-dlp
   ```

2. Start the download server:
   ```bash
   python youtube_to_mp3_server.py
   ```

3. Open `youtube-to-mp3.html` in your browser or visit `http://localhost:5000`

### Usage

1. **Start the server**: Run `python youtube_to_mp3_server.py`
2. **Open the page**: Go to `http://localhost:5000` in your browser
3. **Paste URL**: Enter any YouTube URL (videos, shorts, playlists)
4. **Download**: Click "Download MP3" - the file will be saved to your Downloads folder

### Features

- ✅ High-quality MP3 output (128kbps)
- ✅ Automatic filename generation from video title
- ✅ Handles duplicate filenames
- ✅ Progress indication
- ✅ Supports all YouTube formats (videos, shorts, playlists)
- ✅ Saves directly to Downloads folder

### Requirements

- Python 3.7+
- yt-dlp (automatically downloads FFmpeg if needed)
- Flask web server

**Note**: Please respect copyright laws and only download content you have permission to use.

---

## 🎼 Dashboard Tools

### Precision Audio Player
Advanced music practice tool with sample-accurate playback:

```bash
python precision_player.py
```

**Features:**
- Load audio files (MP3, WAV, FLAC, etc.)
- Sample-accurate looping and seeking
- Multi-track support with device routing
- CSLP marker support for lyrics/notation
- Metronome with count-in functionality
- Keyboard shortcuts and waveform visualization

### File Structure

```
├── balaji_tools.py          # 🎯 Main dashboard application
├── launch_dashboard.py      # 🚀 Simple launcher script
├── precision_player.py      # 🎵 Audio player (server controls removed)
├── youtube_to_mp3_server.py # 🌐 YouTube download server
├── youtube-to-mp3.html      # 🌐 Web interface with status indicator
├── index.html              # 🔄 AnytuneToLRC converter
├── generate_video.py       # 🎬 Video generation tool
├── README.md               # 📖 This file
└── requirements.txt         # 📦 Dependencies
```

### Troubleshooting

**Audio Device Issues**: Ensure audio drivers are up to date and devices are properly configured.

**Server Port Conflicts**: The dashboard automatically handles port 7773 conflicts.

**Missing Tools**: 
- UVR should be installed at `C:\Users\mando\AppData\Local\Programs\Ultimate Vocal Remover\`
- SongIndex requires `G:\My Drive\Music_Scans\app.py`

**Dependencies**:
```bash
pip install PyQt6 numpy sounddevice soundfile flask flask-cors yt-dlp
```
