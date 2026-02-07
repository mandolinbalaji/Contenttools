import json
import os
import uuid
import mimetypes
import subprocess
import base64
import io
from datetime import datetime
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[WARNING] speech_recognition library not installed. Install with: pip install SpeechRecognition")

# Everything lives here - use the directory where this script is located
# This ensures it works regardless of where the batch file is run from
BASE_DIR = Path(__file__).parent.absolute()
print(f"[STARTUP] BASE_DIR: {BASE_DIR}")
print(f"[STARTUP] Script location: {Path(__file__).absolute()}")

DATA_PATH = BASE_DIR / "songs.json"
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_DIR = BASE_DIR / "backups"
MIDI_DIR = BASE_DIR / "midi_files"

app = Flask(__name__, static_folder=None)
_write_lock = False  # single process guard

# Add request logging middleware
@app.before_request
def log_request():
    import sys
    try:
        sys.stderr.write(f"\n[REQUEST] {request.method} {request.path}\n")
        sys.stderr.flush()
    except:
        pass

@app.after_request
def log_response(response):
    import sys
    try:
        sys.stderr.write(f"[RESPONSE] Status: {response.status_code}\n")
        sys.stderr.flush()
    except:
        pass
    return response


def _ensure_json_file():
    if not DATA_PATH.exists():
        DATA_PATH.write_text("[]", encoding="utf-8")


def _normalise_song(s):
    s = dict(s or {})

    # id
    if "id" not in s or not s["id"]:
        s["id"] = str(uuid.uuid4())

    # title
    s["title"] = str(s.get("title", "")).strip()

    # lyrics: accept alternate keys or list, always string
    raw_lyrics = s.get("lyrics", None)
    if raw_lyrics is None or (isinstance(raw_lyrics, str) and raw_lyrics.strip() == ""):
        for k in ("Lyrics", "lyric", "Lyric", "text", "Text", "content", "Content"):
            if k in s and s[k]:
                raw_lyrics = s[k]
                break
    if isinstance(raw_lyrics, list):
        lyr = "\n".join(str(x) for x in raw_lyrics)
    else:
        lyr = str(raw_lyrics or "")
    s["lyrics"] = lyr

    # links: accept string or list, split lines or commas
    raw_links = s.get("links", [])
    links = []
    if isinstance(raw_links, str):
        txt = raw_links.replace("\r", "\n")
        parts = [p.strip() for p in txt.split("\n") if p.strip()]
        if len(parts) == 1 and "," in parts[0]:
            parts = [p.strip() for p in parts[0].split(",")]
        links = parts
    elif isinstance(raw_links, list):
        for x in raw_links:
            if x is None:
                continue
            links.append(str(x).strip())
    s["links"] = [x for x in links if x]

    # tags: accept "a, b", "a; b", or list, dedupe case insensitive
    raw_tags = s.get("tags", [])
    tags = []
    if isinstance(raw_tags, str):
        tags = [t.strip() for t in raw_tags.replace(";", ",").split(",") if t.strip()]
    elif isinstance(raw_tags, list):
        tmp = []
        for t in raw_tags:
            if t is None:
                continue
            tmp.extend([u.strip() for u in str(t).replace(";", ",").split(",") if u.strip()])
        tags = tmp
    seen = set()
    clean_tags = []
    for t in tags:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        clean_tags.append(t)
    s["tags"] = clean_tags

    return s


def _load_songs():
    _ensure_json_file()
    raw = DATA_PATH.read_text(encoding="utf-8").strip()
    if raw == "":
        return []
    data = json.loads(raw)
    if isinstance(data, dict) and "songs" in data:
        data = data.get("songs", [])
    if not isinstance(data, list):
        raise ValueError("songs.json must be a JSON array")
    data = [_normalise_song(x) for x in data]
    _save_songs(data, make_backup=False)  # persist ids or field normalization
    return data


def _save_songs(songs, make_backup=True):
    global _write_lock
    if _write_lock:
        raise RuntimeError("Concurrent write attempted")
    _write_lock = True
    try:
        BACKUP_DIR.mkdir(exist_ok=True)
        if make_backup and DATA_PATH.exists():
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            (BACKUP_DIR / f"songs.{ts}.json").write_text(
                DATA_PATH.read_text(encoding="utf-8"), encoding="utf-8"
            )
        tmp_path = DATA_PATH.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_PATH)
    finally:
        _write_lock = False


@app.get("/")
def index():
    html_path = BASE_DIR / "index.html"
    if not html_path.exists():
        return Response("<h1>index.html not found</h1>", mimetype="text/html")
    return Response(html_path.read_text(encoding="utf-8"), mimetype="text/html; charset=utf-8")


@app.get("/favicon.ico")
def favicon():
    svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><circle cx='32' cy='32' r='28' fill='#ea580c'/></svg>"
    return Response(svg, mimetype="image/svg+xml")


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_config():
    # Chrome DevTools checks for app-specific configuration
    # Return 404 since we don't have any special config
    return jsonify({}), 404





@app.get("/Kanakku.html")
def kanakku():
    """Serve Kanakku phrase timing calculator"""
    kanakku_file = BASE_DIR / "Kanakku.html"
    if not kanakku_file.exists():
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(BASE_DIR, "Kanakku.html")


@app.get("/api/songs")
def api_list():
    try:
        data = _load_songs()
        return jsonify(data)
    except Exception as e:
        return jsonify({"__error__": f"Failed to read songs.json, {e}"}), 500


@app.post("/api/songs")
def api_add():
    try:
        songs = _load_songs()
    except Exception as e:
        return jsonify({"__error__": f"Failed to read songs.json, {e}"}), 500
    payload = request.get_json(force=True) or {}
    new_song = _normalise_song(payload)
    if not new_song["title"]:
        return jsonify({"error": "Title is required"}), 400
    songs.append(new_song)
    _save_songs(songs)
    return jsonify(new_song), 201


@app.put("/api/songs/<song_id>")
def api_edit(song_id):
    try:
        songs = _load_songs()
    except Exception as e:
        return jsonify({"__error__": f"Failed to read songs.json, {e}"}), 500
    for s in songs:
        if s.get("id") == song_id:
            updated = _normalise_song(request.get_json(force=True) or {})
            updated["id"] = song_id
            s.update(updated)
            _save_songs(songs)
            return jsonify(s)
    return jsonify({"error": "Not found"}), 404


@app.delete("/api/songs/<song_id>")
def api_delete(song_id):
    try:
        songs = _load_songs()
    except Exception as e:
        return jsonify({"__error__": f"Failed to read songs.json, {e}"}), 500
    new_list = [s for s in songs if s.get("id") != song_id]
    if len(new_list) == len(songs):
        return jsonify({"error": "Not found"}), 404
    _save_songs(new_list)
    return jsonify({"status": "ok"})


@app.get("/media/<path:relpath>")
def media(relpath):
    rel = relpath.strip().lstrip("/").replace("\\", "/")
    path = (MEDIA_ROOT / rel).resolve()
    if not str(path).startswith(str(MEDIA_ROOT.resolve())):
        return jsonify({"error": "Invalid path"}), 400
    if not path.exists():
        return jsonify({"error": "File not found"}), 404
    guessed, _ = mimetypes.guess_type(str(path))
    return send_from_directory(MEDIA_ROOT, rel, mimetype=guessed, as_attachment=False)






# ===== KANAKKU ENDPOINTS =====
KANAKKU_FILE = BASE_DIR / "kanakku.json"

def _load_kanakkus():
    """Load all saved kanakkus from kanakku.json"""
    if not KANAKKU_FILE.exists():
        return []
    try:
        with open(KANAKKU_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def _save_kanakkus(kanakkus):
    """Save kanakkus to kanakku.json"""
    with open(KANAKKU_FILE, 'w', encoding='utf-8') as f:
        json.dump(kanakkus, f, indent=2, ensure_ascii=False)

def _save_midi_file(kanakku_name, midi_file_data_b64):
    """
    Save MIDI file from base64 data. Overwrites existing file if present.
    
    Args:
        kanakku_name: Name of the kanakku (used in filename)
        midi_file_data_b64: Base64-encoded binary MIDI data
    
    Returns:
        Relative path to saved file, e.g., "midi_files/kanakku-name.mid"
    """
    # Ensure midi_files directory exists
    MIDI_DIR.mkdir(parents=True, exist_ok=True)
    
    # Decode base64 to binary
    try:
        midi_binary = base64.b64decode(midi_file_data_b64)
    except Exception as e:
        print(f"[ERROR] Failed to decode MIDI base64: {e}")
        return None
    
    # Validate MIDI file structure
    if len(midi_binary) < 14:
        print(f"[ERROR] MIDI file too small ({len(midi_binary)} bytes). Expected at least 14 bytes.")
        return None
    
    # Check for MThd header
    if midi_binary[:4] != b'MThd':
        print(f"[ERROR] Invalid MIDI header. Expected 'MThd', got: {midi_binary[:4]}")
        return None
    
    # Check for MTrk header (should be at position 14 minimum for basic MIDI)
    if b'MTrk' not in midi_binary:
        print(f"[ERROR] No MTrk (track) header found in MIDI data. File is incomplete or invalid.")
        print(f"[DEBUG] File hex (first 60 bytes): {midi_binary[:60].hex()}")
        return None
    
    print(f"[INFO] MIDI validation passed: {len(midi_binary)} bytes, contains MThd and MTrk")
    
    # Create filename without timestamp (will overwrite existing file)
    sanitized_name = ''.join(c if c.isalnum() or c in ' -_' else '' for c in kanakku_name)[:50]
    sanitized_name = sanitized_name.replace(' ', '-')
    filename = f"{sanitized_name}.mid"
    filepath = MIDI_DIR / filename
    
    # Save to file (overwrites if exists)
    try:
        with open(filepath, 'wb') as f:
            f.write(midi_binary)
        print(f"[INFO] Saved MIDI file: {filepath}")
        return f"midi_files/{filename}"
    except Exception as e:
        print(f"[ERROR] Failed to save MIDI file: {e}")
        return None


@app.route('/api/kanakkus', methods=['GET'])
def get_kanakkus():
    """Get all saved kanakkus"""
    kanakkus = _load_kanakkus()
    return jsonify(kanakkus)

@app.route('/api/kanakkus', methods=['POST'])
def save_kanakku():
    """Save a new kanakku"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Generate unique ID
    data['id'] = str(uuid.uuid4())
    
    # Save MIDI file if provided
    if data.get('midiFileData'):
        midi_file_path = _save_midi_file(data.get('name', 'kanakku'), data['midiFileData'])
        if midi_file_path:
            data['midiFilePath'] = midi_file_path
        # Remove the binary data from JSON (keep only the path)
        del data['midiFileData']
    
    kanakkus = _load_kanakkus()
    kanakkus.insert(0, data)  # Add to front of list
    _save_kanakkus(kanakkus)
    
    return jsonify(data), 201

@app.route('/api/kanakkus/<kanakku_id>', methods=['PUT'])
def update_kanakku(kanakku_id):
    """Update an existing kanakku"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    kanakkus = _load_kanakkus()
    for i, kanakku in enumerate(kanakkus):
        if kanakku.get('id') == kanakku_id:
            data['id'] = kanakku_id  # Preserve ID
            
            # Save MIDI file if provided
            if data.get('midiFileData'):
                midi_file_path = _save_midi_file(data.get('name', 'kanakku'), data['midiFileData'])
                if midi_file_path:
                    data['midiFilePath'] = midi_file_path
                # Remove the binary data from JSON (keep only the path)
                del data['midiFileData']
            
            kanakkus[i] = data
            _save_kanakkus(kanakkus)
            return jsonify(data)
    
    return jsonify({"error": "Kanakku not found"}), 404

@app.route('/api/kanakkus/<kanakku_id>', methods=['DELETE'])
def delete_kanakku(kanakku_id):
    """Delete a kanakku"""
    kanakkus = _load_kanakkus()
    kanakkus = [k for k in kanakkus if k.get('id') != kanakku_id]
    _save_kanakkus(kanakkus)
    return jsonify({"success": True})

@app.route('/api/open-midi', methods=['POST'])
def open_midi():
    """Open a MIDI file in MuseScore"""
    data = request.get_json()
    if not data or not data.get('filePath'):
        return jsonify({"error": "No filePath provided"}), 400
    
    # Construct full path
    midi_path = BASE_DIR / data['filePath']
    
    # Check if file exists
    if not midi_path.exists():
        return jsonify({"error": "MIDI file not found"}), 404
    
    # Try to open with MuseScore
    try:
        # On Windows, try common MuseScore installation paths
        musescore_paths = [
            "C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe",
            "C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe",
            "C:\\Program Files (x86)\\MuseScore\\bin\\MuseScore.exe",
            "C:\\Program Files\\MuseScore\\bin\\MuseScore.exe",
        ]
        
        opened = False
        for musescore_exe in musescore_paths:
            if os.path.exists(musescore_exe):
                subprocess.Popen([musescore_exe, str(midi_path)])
                opened = True
                break
        
        if not opened:
            # Try using 'start' command on Windows
            os.startfile(str(midi_path))
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Failed to open MIDI file in MuseScore: {e}")
        return jsonify({"error": f"Failed to open file: {str(e)}"}), 500


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio data to text using speech recognition"""
    if not SPEECH_RECOGNITION_AVAILABLE:
        return jsonify({"error": "Speech recognition not available. Install: pip install SpeechRecognition"}), 500
    
    try:
        # Get audio data from request
        audio_data = request.get_data()
        
        if not audio_data:
            return jsonify({"error": "No audio data provided"}), 400
        
        # Create recognizer
        recognizer = sr.Recognizer()
        
        # Convert bytes to AudioData
        try:
            # Assume audio is 16-bit PCM wav data (44.1kHz)
            audio = sr.AudioData(audio_data, 44100, 2)
        except Exception as e:
            print(f"[ERROR] Failed to parse audio data: {e}")
            return jsonify({"error": "Invalid audio format"}), 400
        
        # Try Google Web Speech API first (requires internet)
        try:
            text = recognizer.recognize_google(audio, language='en-US')
            return jsonify({"text": text, "success": True})
        except sr.UnknownValueError:
            return jsonify({"error": "Could not understand audio", "success": False}), 200
        except sr.RequestError as e:
            # Fallback: return error but don't crash
            print(f"[WARNING] Google Speech API error: {e}")
            return jsonify({"error": f"Speech service error: {str(e)}", "success": False}), 200
        except Exception as e:
            print(f"[ERROR] Transcription error: {e}")
            return jsonify({"error": f"Transcription error: {str(e)}", "success": False}), 200
            
    except Exception as e:
        print(f"[ERROR] Transcribe endpoint error: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static HTML files from the base directory"""
    file_path = BASE_DIR / filename
    
    # Security check: prevent directory traversal
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(BASE_DIR.resolve())):
            return jsonify({"error": "Access denied"}), 403
    except:
        return jsonify({"error": "Invalid path"}), 400
    
    # Check if file exists
    if file_path.exists() and file_path.is_file():
        return send_from_directory(BASE_DIR, filename)
    
    return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FLASK APP INITIALIZATION")
    print("="*70)
    print(f"BASE_DIR: {BASE_DIR}")
    print("="*70 + "\n")
    print("Starting server at http://127.0.0.1:5000")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    MIDI_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_json_file()
    app.run(host="127.0.0.1", port=5000, debug=False)
