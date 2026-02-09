import json
import os
import uuid
import mimetypes
import subprocess
import base64
import io
import wave
import logging
import tempfile
import numpy as np
from datetime import datetime
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

# Everything lives here - use the directory where this script is located
# This ensures it works regardless of where the batch file is run from
BASE_DIR = Path(__file__).parent.absolute()

DATA_PATH = BASE_DIR / "songs.json"
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_DIR = BASE_DIR / "backups"
MIDI_DIR = BASE_DIR / "midi_files"

app = Flask(__name__, static_folder=None)
_write_lock = False  # single process guard

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set temp directory for FFmpeg to avoid permission issues
# This must be done before any audio processing
_temp_dir = tempfile.gettempdir()
os.environ['TMPDIR'] = _temp_dir
os.environ['TEMPDIR'] = _temp_dir
os.environ['TMP'] = _temp_dir
logger.info(f"FFmpeg temp directory set to: {_temp_dir}")

# Check if FFmpeg is available for MP4 decoding
def _has_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

FFMPEG_AVAILABLE = _has_ffmpeg()
logger.info(f"FFmpeg available: {FFMPEG_AVAILABLE}")

# ============================================================================
# CARNATIC SWARA RECOGNITION - Constants and CORS Headers
# ============================================================================

# Carnatic Music Swaras (7 notes)
SWARAS = ['s', 'r', 'g', 'm', 'p', 'd', 'n']
SWARA_NAMES = {
    's': 'Sa', 'r': 'Ri', 'g': 'Ga', 'm': 'Ma',
    'p': 'Pa', 'd': 'Dha', 'n': 'Ni'
}

# CORS Headers for Carnatic API
@app.before_request
def cors_before_request():
    """Handle CORS preflight requests for Carnatic API"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

@app.after_request
def cors_after_request(response):
    """Add CORS headers to all responses"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# ============================================================================


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


def _convert_mp4_to_wav_raw(audio_data):
    """Convert MP4/M4A audio to PCM using FFmpeg via pipe"""
    if not FFMPEG_AVAILABLE:
        return None
    
    try:
        logger.debug(f"Attempting FFmpeg MP4 conversion via pipe ({len(audio_data)} bytes)")
        
        # Use FFmpeg with pipe input/output (more reliable than file-based)
        cmd = [
            'ffmpeg',
            '-i', 'pipe:0',           # Read from stdin
            '-f', 'wav',              # Output format
            '-acodec', 'pcm_s16le',   # Audio codec
            '-ar', '16000',           # Sample rate
            '-ac', '1',               # Mono
            '-y',                     # Overwrite output
            '-loglevel', 'error',     # Minimal logging
            'pipe:1'                  # Write to stdout
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=audio_data,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                wav_data = result.stdout
                logger.info(f"✅ MP4→WAV via FFmpeg pipe: {len(audio_data)} → {len(wav_data)} bytes")
                return wav_data
            else:
                stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else 'No error output'
                logger.error(f"FFmpeg conversion failed (code {result.returncode}): {stderr[:100]}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timeout (30s)")
            return None
            
    except Exception as e:
        logger.error(f"FFmpeg pipe conversion error: {e}")
        return None


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

# ============================================================================
# CARNATIC SWARA RECOGNITION - Core Functions
# ============================================================================

def transcribe_audio_chunk(audio_chunk, sr_rate=16000):
    """Transcribe a single audio chunk to get one swara"""
    if not SPEECH_RECOGNITION_AVAILABLE:
        return None
    
    try:
        recognizer = sr.Recognizer()
        # Create AudioData from numpy array
        audio_bytes = (audio_chunk * 32767).astype(np.int16).tobytes()
        audio_data = sr.AudioData(audio_bytes, sr_rate, 2)
        
        # Transcribe
        text = recognizer.recognize_google(audio_data, language='en-US')
        logger.info(f"[Swara] Transcribed chunk: {text}")
        
        # Extract single swara
        swara_result = extract_swaras_from_text(text)
        swara_str = swara_result['swaras'] if isinstance(swara_result, dict) else swara_result
        if swara_str:
            return swara_str[0]  # First swara found
        return None
    except sr.UnknownValueError:
        logger.debug("[Swara] Could not understand audio chunk")
        return None
    except Exception as e:
        logger.debug(f"[Swara] Transcription error: {e}")
        return None


def process_audio_with_chunks(audio_data, sr_rate=16000, chunk_duration=1.0):
    """Process audio in small chunks for swara recognition
    Ideal for individual note recognition in Carnatic music
    """
    if not LIBROSA_AVAILABLE:
        return None, "librosa not available"
    
    try:
        # Settings for chunk processing
        chunk_samples = int(sr_rate * chunk_duration)
        swaras = []
        chunk_info = []
        
        logger.info(f"[Swara] Processing audio: {len(audio_data)} samples at {sr_rate}Hz")
        logger.info(f"[Swara] Chunk size: {chunk_samples} samples ({chunk_duration}s)")
        
        # Process each chunk
        num_chunks = (len(audio_data) + chunk_samples - 1) // chunk_samples
        logger.info(f"[Swara] Total chunks: {num_chunks}")
        
        for i in range(num_chunks):
            start = i * chunk_samples
            end = min(start + chunk_samples, len(audio_data))
            chunk = audio_data[start:end]
            
            # Normalize chunk
            chunk_max = np.max(np.abs(chunk))
            if chunk_max > 0:
                chunk = chunk / chunk_max
            
            # Check if chunk has meaningful energy (not silence)
            energy = np.sum(chunk ** 2) / len(chunk)
            logger.debug(f"[Swara] Chunk {i}: energy={energy:.6f}")
            
            if energy > 0.001:  # Threshold for meaningful audio
                # Transcribe this chunk
                swara = transcribe_audio_chunk(chunk, sr_rate)
                if swara:
                    swaras.append(swara)
                    chunk_info.append({
                        'chunk': i,
                        'time': f"{start/sr_rate:.2f}s-{end/sr_rate:.2f}s",
                        'swara': swara,
                        'energy': float(energy)
                    })
                    logger.info(f"[Swara] Chunk {i}: {swara}")
        
        return ''.join(swaras), chunk_info
        
    except Exception as e:
        logger.error(f"[Swara] Chunk processing error: {e}")
        return None, str(e)


def process_audio_with_progress(audio_data, sr_rate=16000, chunk_duration=1.0):
    """Process audio in chunks with real-time progress updates
    
    Yields progress dictionaries for each chunk processed.
    Each progress dict contains: chunk_num, total_chunks, percentage, swara, transcribed_text, time
    """
    if not LIBROSA_AVAILABLE:
        yield {"error": "librosa not available", "percentage": 0}
        return
    
    try:
        # Settings for chunk processing
        chunk_samples = int(sr_rate * chunk_duration)
        swaras = []
        num_chunks = (len(audio_data) + chunk_samples - 1) // chunk_samples
        
        logger.info(f"[Swara/Stream] Starting: {num_chunks} chunks of {chunk_duration}s")
        
        # Yield initial status
        yield {
            "status": "starting",
            "total_chunks": num_chunks,
            "percentage": 0,
            "message": f"Processing audio: {len(audio_data)} samples at {sr_rate}Hz"
        }
        
        processed_chunks = 0
        
        # Process each chunk
        energy_threshold = 0.00001  # Very low threshold to catch all speech
        
        for i in range(num_chunks):
            start = i * chunk_samples
            end = min(start + chunk_samples, len(audio_data))
            chunk = audio_data[start:end]
            time_range = f"{start/sr_rate:.2f}s-{end/sr_rate:.2f}s"
            
            # Normalize chunk
            chunk_max = np.max(np.abs(chunk))
            if chunk_max > 0:
                chunk = chunk / chunk_max
            
            # Check if chunk has meaningful energy
            energy = np.sum(chunk ** 2) / len(chunk)
            logger.info(f"[Swara/Stream] Chunk {i}: energy={energy:.8f} (threshold={energy_threshold:.8f})")
            
            # Always try to transcribe all chunks (even low-energy ones)
            if True:  # Always process
                # Transcribe this chunk
                recognizer = sr.Recognizer()
                audio_bytes = (chunk * 32767).astype(np.int16).tobytes()
                audio_data_sr = sr.AudioData(audio_bytes, sr_rate, 2)
                
                transcribed_text = None
                swara = None
                
                try:
                    logger.info(f"[Swara/Stream] Chunk {i}: Attempting transcription...")
                    transcribed_text = recognizer.recognize_google(audio_data_sr, language='en-US')
                    logger.info(f"[Swara/Stream] Chunk {i}: 🎤 Heard: '{transcribed_text}'")
                    
                    swara_result = extract_swaras_from_text(transcribed_text)
                    swara_str = swara_result['swaras'] if isinstance(swara_result, dict) else swara_result
                    logger.info(f"[Swara/Stream] Chunk {i}: Extracted swaras: '{swara_str}' (method: {swara_result.get('method', 'unknown') if isinstance(swara_result, dict) else 'simple'})")
                    
                    if swara_str:
                        first_swara = swara_str[0]
                        swaras.append(first_swara)
                        logger.info(f"[Swara/Stream] Chunk {i}: ✅ RECOGNIZED: '{first_swara}' from '{transcribed_text}'")
                    
                    # Yield progress with transcribed text
                    swara_display = swara_str[0] if swara_str else "—"
                    yield {
                        "status": "processing",
                        "chunk_num": i,
                        "total_chunks": num_chunks,
                        "percentage": int((i + 1) / num_chunks * 100),
                        "transcribed_text": transcribed_text,
                        "swara": swara_display,
                        "time": time_range,
                        "energy": float(energy)
                    }
                    
                except sr.UnknownValueError:
                    logger.warning(f"[Swara/Stream] Chunk {i}: ⚠️  Could not understand audio (no speech detected)")
                    yield {
                        "status": "processing",
                        "chunk_num": i,
                        "total_chunks": num_chunks,
                        "percentage": int((i + 1) / num_chunks * 100),
                        "transcribed_text": "—",
                        "swara": "—",
                        "time": time_range,
                        "energy": float(energy),
                        "skip_reason": "not_recognized"
                    }
                except Exception as e:
                    logger.warning(f"[Swara/Stream] Chunk {i}: ❌ Error: {e}")
                    yield {
                        "status": "processing",
                        "chunk_num": i,
                        "total_chunks": num_chunks,
                        "percentage": int((i + 1) / num_chunks * 100),
                        "transcribed_text": "—",
                        "swara": "—",
                        "time": time_range,
                        "error": str(e)
                    }
            
            # No longer skip chunks by energy - process all
        
        # Final result
        yield {
            "status": "complete",
            "percentage": 100,
            "swaras": ''.join(swaras),
            "total_swaras": len(swaras),
            "message": f"✨ Complete! Recognized {len(swaras)} swaras"
        }
        
    except Exception as e:
        logger.error(f"[Swara/Stream] Error: {e}")
        yield {"status": "error", "error": str(e), "percentage": 0}

# ============================================================================


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
        logger.error(f"Failed to decode MIDI base64: {e}")
        return None
    
    # Validate MIDI file structure
    if len(midi_binary) < 14:
        logger.error(f"MIDI file too small ({len(midi_binary)} bytes)")
        return None
    
    # Check for MThd header
    if midi_binary[:4] != b'MThd':
        return None
    
    # Check for MTrk header (should be at position 14 minimum for basic MIDI)
    if b'MTrk' not in midi_binary:
        return None
    
    # Create filename without timestamp (will overwrite existing file)
    sanitized_name = ''.join(c if c.isalnum() or c in ' -_' else '' for c in kanakku_name)[:50]
    sanitized_name = sanitized_name.replace(' ', '-')
    filename = f"{sanitized_name}.mid"
    filepath = MIDI_DIR / filename
    
    # Save to file (overwrites if exists)
    try:
        with open(filepath, 'wb') as f:
            f.write(midi_binary)
        return f"midi_files/{filename}"
    except Exception as e:
        logger.error(f"Failed to save MIDI file: {e}")
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
        logger.error(f"Failed to open MIDI file: {e}")
        return jsonify({"error": f"Failed to open file: {str(e)}"}), 500


def extract_swaras_from_text(text, recognized_text=""):
    """
    Extract swaras (S, R, G, M, P, D, N) from recognized text.
    Designed for Carnatic music notation - focuses on the 7 basic notes.
    
    Strategy 1: Direct character matching (s, r, g, m, p, d, n)
    Strategy 2: Phonetic matching - handle how amateurs pronounce notes
    Strategy 3: Common misrecognitions from speech API
    """
    valid_swaras = set(['s', 'r', 'g', 'm', 'p', 'd', 'n'])
    
    # Strategy 1: Direct extraction
    text_lower = text.lower()
    cleaned = text_lower.replace(' ', '')
    
    direct_swaras = ''
    direct_ignored = ''
    for char in cleaned:
        if char in valid_swaras:
            direct_swaras += char
        elif char != '':
            direct_ignored += char
    
    # Strategy 2 & 3: Phonetic extraction for amateur Carnatic singers
    # These patterns handle:
    # - Different pronunciation variations (sa/sah, pa/pah, etc)
    # - Elongated vowels (saaaa = s)
    # - Common speech recognition errors
    # - Note sequences that sound similar
    
    phonetic_corrections = {
        # Elongated notes (common in singing)
        'saaaa': 's', 'saaa': 's', 'saa': 's',
        'raaaa': 'r', 'raaa': 'r', 'raa': 'r',
        'gaaaa': 'g', 'gaaa': 'g', 'gaa': 'g',
        'maaaa': 'm', 'maaa': 'm', 'maa': 'm',
        'paaaa': 'p', 'paaa': 'p', 'paa': 'p',
        'daaaa': 'd', 'daaa': 'd', 'daa': 'd',
        'naaaa': 'n', 'naaa': 'n', 'naa': 'n',
        
        # With consonant endings (how people naturally sing)
        'sah': 's', 'rah': 'r', 'gah': 'g', 'mah': 'm', 'pah': 'p', 'dah': 'd', 'nah': 'n',
        'shas': 'ss', 'rahs': 'rr', 'gahs': 'gg', 'mahs': 'mm', 'pahs': 'pp', 'dahs': 'dd', 'nahs': 'nn',
        
        # Long vowel variations
        'saw': 's', 'raw': 'r', 'gaw': 'g', 'maw': 'm', 'paw': 'p', 'daw': 'd', 'naw': 'n',
        
        # Common note name pronunciations (full swaras)
        'sha': 's', 're': 'r', 'ri': 'r', 'ga': 'g', 'ma': 'm', 'pa': 'p', 'dha': 'd', 'ni': 'n',
        'resh': 'r', 'gam': 'g', 'mam': 'm', 'pam': 'p', 'dam': 'd', 'nam': 'n',
        
        # Common sequences (adjacent notes)
        'sa re': 'sr', 'sa ri': 'sr', 're ga': 'rg', 'ga ma': 'gm', 'ma pa': 'mp', 'pa dha': 'pd', 'dha ni': 'dn',
        'saraga': 'srg', 'resaga': 'rsga', 'gama': 'gm', 'madha': 'md', 'pani': 'pn',
        
        # Very common amateur patterns
        'shag': 'sg', 'shap': 'sp', 'shard': 'srd', 'sharp': 'srp',
        'rya': 'r', 'ria': 'r', 'ryga': 'rg',
        'pee': 'p', 'pi': 'p', 'pine': 'p',
        'nee': 'n', 'knee': 'n', 'nigh': 'n',
        
        # Repetitions in singing
        'ssss': 'ssss', 'rrrr': 'rrrr', 'gggg': 'gggg', 'mmmm': 'mmmm', 'pppp': 'pppp', 'dddd': 'dddd', 'nnnn': 'nnnn',
        'nini': 'nn', 'ninini': 'nnn', 'papa': 'pp', 'papapa': 'ppp', 'mama': 'mm', 'mamama': 'mmm',
        'didi': 'dd', 'dididi': 'ddd', 'gigi': 'gg', 'gigigi': 'ggg', 'riri': 'rr', 'rarara': 'rr',
        
        # Speech API common misrecognitions
        'sea': 's', 'see': 's', 'rea': 'r', 'gee': 'g', 'may': 'm', 'pay': 'p', 'dee': 'd', 'pea': 'p',
        'song': '', 'say': 's', 'okay': '', 'thank': '',  # Filter out non-notes
        
        # Syllable patterns with musical endings
        'sap': 's', 'sam': 's', 'san': 's', 'sap': 's',
        'rap': 'r', 'ram': 'r', 'ran': 'r', 'ramp': 'r',
        'gap': 'g', 'gam': 'g', 'gan': 'g', 'gams': 'g',
        'mam': 'm', 'man': 'm', 'map': 'm', 'mamp': 'm',
        'pam': 'p', 'pan': 'p', 'map': 'p', 'pans': 'p',
        'dam': 'd', 'dan': 'd', 'damp': 'd', 'dans': 'd', 'dun': 'd',
        'nam': 'n', 'nan': 'n', 'nap': 'n', 'nans': 'n',
        
        # Alternating patterns (like scalar runs)
        'shrig': 'srg', 'rigma': 'rgm', 'gampa': 'gmp', 'mapda': 'mpd', 'padni': 'pdn',
    }
    
    phonetic_swaras = text_lower
    # Apply corrections in order of longest first (to avoid partial replacements)
    for word_pattern in sorted(phonetic_corrections.keys(), key=len, reverse=True):
        swara_pattern = phonetic_corrections[word_pattern]
        phonetic_swaras = phonetic_swaras.replace(word_pattern, swara_pattern)
    
    # Extract swaras from phonetically corrected text
    phonetic_cleaned = phonetic_swaras.replace(' ', '')
    phonetic_extracted = ''
    phonetic_ignored = ''
    for char in phonetic_cleaned:
        if char in valid_swaras:
            phonetic_extracted += char
        elif char != '':
            phonetic_ignored += char
    
    # Return best interpretation (prefer phonetic if it finds notes, else direct)
    best_swaras = phonetic_extracted if phonetic_extracted else direct_swaras
    
    return {
        'swaras': best_swaras,           # The extracted notes (S R G M P D N)
        'method': 'phonetic' if phonetic_extracted else 'direct',
        'direct': direct_swaras,         # Raw character extraction
        'direct_ignored': direct_ignored,
        'phonetic': phonetic_extracted,  # Phonetic-based extraction
        'phonetic_ignored': phonetic_ignored,
        'raw_text': text                 # Original recognized text
    }








@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio data to text using speech recognition"""
    if not SPEECH_RECOGNITION_AVAILABLE:
        return jsonify({"error": "Speech recognition not available"}), 500
    
    try:
        # Get audio data from request
        audio_data = request.get_data()
        audio_size = len(audio_data)
        
        if not audio_data or audio_size < 100:
            return jsonify({"error": f"Audio too small ({audio_size} bytes) - needs at least 100 bytes", "success": False}), 200
        
        # Log audio signature for debugging
        hex_sig = audio_data[:16].hex() if audio_size >= 16 else audio_data.hex()
        logger.info(f"Received audio: {audio_size} bytes, signature: {hex_sig}")
        
        # Create recognizer
        recognizer = sr.Recognizer()
        audio_sr = None
        
        # Check if this is a WAV file (check RIFF header)
        is_wav = audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'
        is_webm = len(audio_data) > 4 and audio_data[0] == 0x1a and audio_data[1] == 0x45 and audio_data[2] == 0xdf and audio_data[3] == 0xa3
        # Check for MP4/M4A file - multiple signatures for different MP4 variants
        is_mp4 = (b'ftyp' in audio_data[:32] or                    # Standard MP4 ftyp box
                  (len(audio_data) > 4 and audio_data[4:8] == b'ftyp') or  # ftyp at offset 4
                  b'mdat' in audio_data[:16] or                    # Media data box
                  b'moov' in audio_data[:200] or                   # Movie box
                  (len(audio_data) > 10 and audio_data[4:8] == b'\x00\x00\x00\x00') or  # Extended size
                  (len(audio_data) > 4 and audio_data[0:3] == b'\x00\x00\x20'))  # M4A signature
        
        logger.info(f"Audio detection summary: WAV={is_wav}, WebM={is_webm}, MP4={is_mp4}, size={audio_size}, sig={audio_data[:16].hex()}")
        
        if is_wav:
            # Parse WAV directly to check specs
            try:
                wav_stream = io.BytesIO(audio_data)
                with wave.open(wav_stream, 'rb') as wav:
                    frames = wav.readframes(wav.getnframes())
                    sample_rate = wav.getframerate()
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    num_frames = wav.getnframes()
                
                # If it's already 16kHz mono 16-bit, use it directly
                if sample_rate == 16000 and channels == 1 and sample_width == 2:
                    audio_sr = sr.AudioData(frames, 16000, 2)
                else:
                    # Need to resample/convert
                    try:
                        from pydub import AudioSegment
                        # Create AudioSegment from raw bytes
                        audio = AudioSegment(
                            data=frames,
                            sample_width=sample_width,
                            frame_rate=sample_rate,
                            channels=channels
                        )
                        
                        # Convert to 16kHz mono 16-bit
                        audio = audio.set_channels(1).set_sample_width(2).set_frame_rate(16000)
                        
                        # Get the raw audio bytes
                        converted_frames = audio.raw_data
                        audio_sr = sr.AudioData(converted_frames, 16000, 2)
                        
                    except Exception as e:
                        # Fallback: try to use the frames as-is
                        audio_sr = sr.AudioData(frames, sample_rate, sample_width)
            
            except Exception as e:
                logger.error(f"WAV parsing failed: {e}")
                return jsonify({"error": f"Could not parse audio: {str(e)}", "success": False, "stage": "wav_parse"}), 200
        
        elif is_webm:
            # WebM file - use pydub conversion  
            try:
                from pydub import AudioSegment
                logger.info(f"Processing WebM audio ({audio_size} bytes)")
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
                
                # Convert to 16kHz mono 16-bit
                audio = audio.set_channels(1).set_sample_width(2).set_frame_rate(16000)
                converted_frames = audio.raw_data
                audio_sr = sr.AudioData(converted_frames, 16000, 2)
                logger.info(f"WebM converted successfully ({len(converted_frames)} bytes)")
            except Exception as e:
                logger.error(f"WebM processing error: {e}")
                return jsonify({"error": f"WebM error: Decoding failed - {str(e)[:80]}", "success": False, "stage": "webm_parse"}), 200
        
        elif is_mp4:
            # MP4/M4A file - use FFmpeg or pydub
            try:
                from pydub import AudioSegment
                logger.info(f"Processing MP4 audio ({audio_size} bytes)")
                
                # First try pydub
                audio = None
                for fmt in ['m4a', 'mp4', 'aac']:
                    try:
                        logger.debug(f"Trying pydub MP4 format: {fmt}")
                        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=fmt)
                        logger.info(f"✅ Pydub loaded MP4 as {fmt}")
                        break
                    except Exception as e:
                        logger.debug(f"Pydub {fmt} failed: {str(e)[:50]}")
                
                # If pydub failed, try FFmpeg conversion
                if not audio and FFMPEG_AVAILABLE:
                    logger.info("Pydub failed, trying FFmpeg conversion for MP4...")
                    wav_data = _convert_mp4_to_wav_raw(audio_data)
                    if wav_data:
                        try:
                            audio = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")
                            logger.info("✅ FFmpeg successfully converted MP4 to WAV")
                        except Exception as e:
                            logger.error(f"Failed to load FFmpeg-converted WAV: {e}")
                            audio = None
                
                if not audio:
                    raise ValueError("MP4 decoding failed - pydub and FFmpeg both failed")
                
                # Convert to 16kHz mono 16-bit (in case it's not already)
                audio = audio.set_channels(1).set_sample_width(2).set_frame_rate(16000)
                converted_frames = audio.raw_data
                audio_sr = sr.AudioData(converted_frames, 16000, 2)
                logger.info(f"✅ MP4 processed successfully ({len(converted_frames)} bytes)")
                
            except Exception as e:
                logger.error(f"MP4 processing error: {e}")
                return jsonify({"error": f"MP4 error: {str(e)[:80]}", "success": False, "stage": "mp4_parse"}), 200
        
        else:
            # Unknown format - try to detect and convert
            try:
                from pydub import AudioSegment
                logger.info(f"Auto-detecting audio format ({audio_size} bytes)")
                
                # Try to auto-detect
                audio = None
                
                # First, try without specifying format (let pydub detect)
                try:
                    audio = AudioSegment.from_file(io.BytesIO(audio_data))
                    logger.info("Format auto-detected successfully by pydub")
                except Exception as e:
                    logger.debug(f"Pydub auto-detection failed: {e}")
                    audio = None
                
                # If that didn't work, try specific formats in priority order
                if not audio:
                    # MP4/M4A must be tried first since browser often sends audio/mp4
                    format_list = ['m4a', 'mp4', 'aac', 'mp3', 'ogg', 'flac', 'wav', 'webm']
                    for fmt in format_list:
                        try:
                            logger.debug(f"Trying pydub format: {fmt}")
                            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=fmt)
                            logger.info(f"✅ Successfully loaded audio as {fmt} format")
                            break
                        except Exception as e:
                            logger.debug(f"Failed to load as {fmt}: {str(e)[:50]}")
                            continue
                
                # If pydub still failed and we have FFmpeg, try MP4 conversion via FFmpeg
                if not audio and FFMPEG_AVAILABLE:
                    logger.info("Trying MP4 conversion via FFmpeg...")
                    wav_data = _convert_mp4_to_wav_raw(audio_data)
                    if wav_data:
                        try:
                            # Load the converted WAV
                            audio = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")
                            logger.info("✅ Successfully converted audio via FFmpeg")
                        except Exception as e:
                            logger.error(f"Failed to load FFmpeg-converted WAV: {e}")
                            audio = None
                
                if not audio:
                    error_msg = (f"Could not decode audio format with pydub "
                                f"(tried: m4a, mp4, aac, mp3, ogg, flac, wav, webm). "
                                f"FFmpeg available: {FFMPEG_AVAILABLE}")
                    logger.error(f"Format detection failed: {error_msg}")
                    raise ValueError(error_msg)
                
                # Convert to mono, 16-bit, 16kHz
                logger.info(f"Converting from {audio.frame_rate}Hz {audio.channels}ch to 16kHz mono")
                audio = audio.set_channels(1).set_sample_width(2).set_frame_rate(16000)
                converted_frames = audio.raw_data
                audio_sr = sr.AudioData(converted_frames, 16000, 2)
                logger.info(f"✅ Audio converted successfully ({len(converted_frames)} bytes)")
                
            except Exception as e:
                logger.error(f"Format conversion failed: {e}")
                return jsonify({"error": f"Unsupported audio format: {str(e)[:100]}", "success": False, "stage": "format"}), 200
        
        if not audio_sr:
            return jsonify({"error": "Failed to process audio", "success": False, "stage": "audio_load"}), 200
        
        # Try Google Web Speech API
        try:
            text = recognizer.recognize_google(audio_sr, language='en-US')
            logger.info(f"Transcribed text: {text}")
            
            # Extract swaras from the recognized text
            swara_result = extract_swaras_from_text(text)
            
            return jsonify({
                "text": text,
                "swaras": swara_result['swaras'],
                "method": swara_result['method'],
                "success": True,
                "debug": {
                    "raw_text": text,
                    "direct_match": swara_result['direct'],
                    "phonetic_match": swara_result['phonetic']
                }
            })
        except sr.UnknownValueError as e:
            return jsonify({
                "error": "Google could not understand your speech - try speaking clearer, slower, or check microphone quality",
                "success": False,
                "stage": "recognition"
            }), 200
        except sr.RequestError as e:
            return jsonify({
                "error": f"Speech service error - {str(e)[:100]}",
                "success": False,
                "stage": "api_request"
            }), 200
        except Exception as e:
            return jsonify({"error": f"Error: {str(e)[:100]}", "success": False, "stage": "transcription"}), 200
            
    except Exception as e:
        logger.error(f"Transcribe endpoint error: {e}")
        return jsonify({"error": f"Server error: {str(e)[:100]}", "success": False, "stage": "server"}), 500


@app.route('/api/test-swara/<filename>', methods=['GET'])
def test_swara_recognition(filename):
    """Test swara recognition with WAV files from media folder"""
    try:
        # Safely construct the file path
        file_path = MEDIA_ROOT / filename
        file_path = file_path.resolve()
        
        # Security check - ensure file is in media folder
        if not str(file_path).startswith(str(MEDIA_ROOT.resolve())):
            return jsonify({"error": "Access denied", "success": False}), 403
        
        # Check file exists
        if not file_path.exists() or not file_path.is_file():
            return jsonify({"error": f"File not found: {filename}", "success": False}), 404
        
        # Read the audio file
        audio_data = file_path.read_bytes()
        logger.info(f"Testing swara recognition with file: {filename} ({len(audio_data)} bytes)")
        
        # Create recognizer
        recognizer = sr.Recognizer()
        audio_sr = None
        
        # Check if it's a WAV file
        is_wav = audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'
        
        if is_wav:
            try:
                wav_stream = io.BytesIO(audio_data)
                with wave.open(wav_stream, 'rb') as wav:
                    frames = wav.readframes(wav.getnframes())
                    sample_rate = wav.getframerate()
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                
                logger.info(f"WAV file: {sample_rate}Hz, {channels}ch, {sample_width} bytes per sample")
                
                # If it's already 16kHz mono 16-bit, use it directly
                if sample_rate == 16000 and channels == 1 and sample_width == 2:
                    audio_sr = sr.AudioData(frames, 16000, 2)
                else:
                    # Convert using pydub
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment(
                            data=frames,
                            sample_width=sample_width,
                            frame_rate=sample_rate,
                            channels=channels
                        )
                        audio = audio.set_channels(1).set_sample_width(2).set_frame_rate(16000)
                        converted_frames = audio.raw_data
                        audio_sr = sr.AudioData(converted_frames, 16000, 2)
                        logger.info(f"WAV converted to 16kHz mono")
                    except Exception as e:
                        # Fallback: try to use as-is
                        audio_sr = sr.AudioData(frames, sample_rate, sample_width)
                        logger.warning(f"WAV used as-is: {e}")
            
            except Exception as e:
                logger.error(f"WAV parsing failed: {e}")
                return jsonify({"error": f"WAV parsing error: {str(e)}", "success": False}), 400
        else:
            return jsonify({"error": "File must be WAV format", "success": False}), 400
        
        if not audio_sr:
            return jsonify({"error": "Failed to load audio", "success": False}), 400
        
        # Transcribe using Google Speech API
        try:
            text = recognizer.recognize_google(audio_sr, language='en-US')
            logger.info(f"Transcribed: {text}")
            
            # Extract swaras
            swara_result = extract_swaras_from_text(text)
            
            return jsonify({
                "filename": filename,
                "text": text,
                "swaras": swara_result['swaras'],
                "method": swara_result['method'],
                "success": True,
                "debug": {
                    "raw_text": text,
                    "direct_match": swara_result['direct'],
                    "phonetic_match": swara_result['phonetic'],
                    "audio_info": f"{len(audio_data)} bytes, format: WAV"
                }
            })
        except sr.UnknownValueError:
            return jsonify({
                "filename": filename,
                "error": "Could not understand audio - try a clearer recording",
                "success": False
            }), 200
        except sr.RequestError as e:
            return jsonify({
                "filename": filename,
                "error": f"Speech service error: {str(e)[:80]}",
                "success": False
            }), 200
            
    except Exception as e:
        logger.error(f"Test swara endpoint error: {e}")
        return jsonify({"error": f"Server error: {str(e)[:100]}", "success": False}), 500


def _convert_webm_to_wav_bytes(audio_bytes):
    """Convert WebM/MP4 audio bytes to WAV using FFmpeg pipe
    
    Args:
        audio_bytes: Raw audio data (WebM, MP4, etc)
    
    Returns:
        WAV bytes if successful, None if conversion fails
    """
    if not FFMPEG_AVAILABLE:
        logger.warning("[Swara] FFmpeg not available for WebM conversion")
        return None
    
    try:
        logger.info(f"[Swara] Converting WebM to WAV via FFmpeg ({len(audio_bytes)} bytes)")
        
        # Use FFmpeg with pipe input/output for WebM/MP4 conversion
        cmd = [
            'ffmpeg',
            '-i', 'pipe:0',           # Read from stdin
            '-f', 'wav',              # Output WAV format
            '-acodec', 'pcm_s16le',   # PCM 16-bit little-endian
            '-ar', '16000',           # Sample rate
            '-ac', '1',               # Mono
            '-y',                     # Overwrite output
            '-loglevel', 'error',     # Minimal logging
            'pipe:1'                  # Write to stdout
        ]
        
        result = subprocess.run(
            cmd,
            input=audio_bytes,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            wav_data = result.stdout
            logger.info(f"[Swara] ✅ WebM→WAV conversion: {len(audio_bytes)} → {len(wav_data)} bytes")
            return wav_data
        else:
            stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else 'No error output'
            logger.error(f"[Swara] FFmpeg conversion failed (code {result.returncode}): {stderr[:100]}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("[Swara] FFmpeg conversion timeout (30s)")
        return None
    except Exception as e:
        logger.error(f"[Swara] FFmpeg conversion error: {e}")
        return None


# ============================================================================

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_and_recognize():
    """Upload audio file and recognize swaras using chunk-based processing
    
    Supports: WAV, MP3, OGG, FLAC, WebM, MP4 (WebM/MP4 converted via FFmpeg)
    Returns: Recognized swaras + chunk analysis info
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided", "success": False}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({"error": "No file selected", "success": False}), 400
        
        logger.info(f"[API/upload] Received file: {file.filename} (type: {file.content_type})")
        
        # Read audio bytes from FileStorage
        audio_bytes = file.read()
        logger.info(f"[API/upload] File size: {len(audio_bytes)} bytes")
        
        # Try to load with librosa directly first
        audio_data = None
        sr_rate = None
        
        try:
            # Try loading directly (works for WAV, MP3, OGG, etc)
            import io
            audio_data, sr_rate = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
            logger.info(f"[API/upload] ✅ Loaded audio directly: {len(audio_data)} samples at {sr_rate}Hz")
        except Exception as e:
            logger.warning(f"[API/upload] Direct load failed: {e}")
            
            # Check if it's WebM or MP4 format
            if file.content_type in ['audio/webm', 'audio/mp4', 'video/mp4'] or \
               file.filename.lower().endswith(('.webm', '.mp4', '.m4a')):
                
                logger.info("[API/upload] Attempting FFmpeg conversion for WebM/MP4...")
                
                # Convert using FFmpeg
                wav_bytes = _convert_webm_to_wav_bytes(audio_bytes)
                
                if wav_bytes:
                    try:
                        # Try loading the converted WAV
                        audio_data, sr_rate = librosa.load(io.BytesIO(wav_bytes), sr=16000, mono=True)
                        logger.info(f"[API/upload] ✅ Loaded converted audio: {len(audio_data)} samples at {sr_rate}Hz")
                    except Exception as e2:
                        logger.error(f"[API/upload] Failed to load converted audio: {e2}")
                        return jsonify({"error": f"Could not load converted audio: {str(e2)}", "success": False}), 400
                else:
                    return jsonify({"error": "WebM/MP4 format requires FFmpeg. Format conversion failed.", "success": False}), 400
            else:
                return jsonify({"error": f"Could not load audio format. Error: {str(e)}", "success": False}), 400
        
        # Ensure we have audio data
        if audio_data is None or sr_rate is None:
            return jsonify({"error": "Failed to load audio data", "success": False}), 400
        
        # Process in chunks
        swaras, chunk_info = process_audio_with_chunks(audio_data, sr_rate, chunk_duration=0.5)
        
        if swaras is None:
            return jsonify({"error": chunk_info, "success": False}), 400
        
        logger.info(f"[API/upload] Final result: {swaras}")
        
        return jsonify({
            "swaras": swaras,
            "chunks": chunk_info,
            "success": True,
            "info": f"Recognized {len(swaras)} swaras in {len(chunk_info)} chunks"
        })
        
    except Exception as e:
        logger.error(f"[API/upload] Error: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/api/upload-stream', methods=['POST', 'OPTIONS'])
def upload_with_stream():
    """Upload audio file and stream progress updates (Server-Sent Events)
    
    Returns real-time progress as JSON events showing each chunk's transcription
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    # Extract file from request BEFORE creating generator (must be in request context)
    if 'audio' not in request.files:
        return Response(
            f"data: {json.dumps({'error': 'No audio file provided'})}\n\n",
            mimetype='text/event-stream'
        )
    
    file = request.files['audio']
    if file.filename == '':
        return Response(
            f"data: {json.dumps({'error': 'No file selected'})}\n\n",
            mimetype='text/event-stream'
        )
    
    # Read audio bytes while we're still in request context
    audio_bytes = file.read()
    file_content_type = file.content_type
    file_filename = file.filename
    
    logger.info(f"[API/upload-stream] Received file: {file_filename} (type: {file_content_type})")
    logger.info(f"[API/upload-stream] File size: {len(audio_bytes)} bytes")
    
    # Now create generator that only uses the extracted data, not request object
    def stream_progress():
        try:
            import io
            
            # Try to load with librosa directly first
            audio_data = None
            sr_rate = None
            
            try:
                # Try loading directly (works for WAV, MP3, OGG, etc)
                audio_data, sr_rate = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
                logger.info(f"[API/upload-stream] ✅ Loaded audio directly: {len(audio_data)} samples at {sr_rate}Hz")
            except Exception as e:
                logger.warning(f"[API/upload-stream] Direct load failed: {e}")
                
                # Check if it's WebM or MP4 format
                if file_content_type in ['audio/webm', 'audio/mp4', 'video/mp4'] or \
                   file_filename.lower().endswith(('.webm', '.mp4', '.m4a')):
                    
                    logger.info("[API/upload-stream] Attempting FFmpeg conversion for WebM/MP4...")
                    yield f"data: {json.dumps({'status': 'converting', 'message': 'Converting WebM/MP4 to WAV...'})}\n\n"
                    
                    # Convert using FFmpeg
                    wav_bytes = _convert_webm_to_wav_bytes(audio_bytes)
                    
                    if wav_bytes:
                        try:
                            # Try loading the converted WAV
                            audio_data, sr_rate = librosa.load(io.BytesIO(wav_bytes), sr=16000, mono=True)
                            logger.info(f"[API/upload-stream] ✅ Loaded converted audio: {len(audio_data)} samples at {sr_rate}Hz")
                        except Exception as e2:
                            logger.error(f"[API/upload-stream] Failed to load converted audio: {e2}")
                            yield f"data: {json.dumps({'error': f'Could not load converted audio: {str(e2)}'})}\n\n"
                            return
                    else:
                        yield f"data: {json.dumps({'error': 'WebM/MP4 conversion failed. FFmpeg may not be available.'})}\n\n"
                        return
                else:
                    yield f"data: {json.dumps({'error': f'Could not load audio format: {str(e)}'})}\n\n"
                    return
            
            # Ensure we have audio data
            if audio_data is None or sr_rate is None:
                yield f"data: {json.dumps({'error': 'Failed to load audio data'})}\n\n"
                return
            
            # Process in chunks with progress streaming
            for progress in process_audio_with_progress(audio_data, sr_rate, chunk_duration=1.0):
                yield f"data: {json.dumps(progress)}\n\n"
                
        except Exception as e:
            logger.error(f"[API/upload-stream] Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_progress(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Content-Type': 'text/event-stream'
        }
    )


def test_file_recognition(filename):
    """Test swara recognition with pre-recorded file from media folder
    
    Example files: A-audio.wav, srgmpdns.wav
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Safety check
        file_path = MEDIA_ROOT / filename
        if not file_path.exists():
            return jsonify({"error": f"File not found: {filename}", "success": False}), 404
        
        logger.info(f"[API/test-file] Testing with file: {filename}")
        
        # Load audio using librosa
        try:
            audio_data, sr_rate = librosa.load(str(file_path), sr=16000, mono=True)
            logger.info(f"[API/test-file] Loaded {filename}: {len(audio_data)} samples at {sr_rate}Hz")
        except Exception as e:
            logger.error(f"[API/test-file] Failed to load {filename}: {e}")
            return jsonify({"error": f"Could not load audio: {str(e)}", "success": False}), 400
        
        # Process in chunks
        swaras, chunk_info = process_audio_with_chunks(audio_data, sr_rate, chunk_duration=0.5)
        
        if swaras is None:
            return jsonify({"error": chunk_info, "success": False}), 400
        
        logger.info(f"[API/test-file] Result for {filename}: {swaras}")
        
        return jsonify({
            "filename": filename,
            "swaras": swaras,
            "chunks": chunk_info,
            "success": True,
            "info": f"Recognized {len(swaras)} swaras in {len(chunk_info)} chunks"
        })
        
    except Exception as e:
        logger.error(f"[API/test-file] Error: {e}")
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# SwaraScript App Server
# ============================================================================

@app.route('/SwaraScript/<path:filepath>')
def serve_swarascript(filepath):
    """Serve SwaraScript app files with proper MIME types"""
    swarascript_dir = BASE_DIR / 'SwaraScript'
    file_path = swarascript_dir / filepath
    
    # Security check: prevent directory traversal
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(swarascript_dir.resolve())):
            return jsonify({"error": "Access denied"}), 403
    except:
        return jsonify({"error": "Invalid path"}), 400
    
    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"error": "File not found"}), 404
    
    # Set proper MIME types
    mime_type = 'application/octet-stream'
    if filepath.endswith('.tsx'):
        mime_type = 'application/typescript'
    elif filepath.endswith('.ts'):
        mime_type = 'application/typescript'
    elif filepath.endswith('.jsx'):
        mime_type = 'text/jsx'
    elif filepath.endswith('.js'):
        mime_type = 'application/javascript'
    elif filepath.endswith('.css'):
        mime_type = 'text/css'
    elif filepath.endswith('.json'):
        mime_type = 'application/json'
    elif filepath.endswith('.html'):
        mime_type = 'text/html'
    elif filepath.endswith('.svg'):
        mime_type = 'image/svg+xml'
    elif filepath.endswith(('.png', '.jpg', '.jpeg')):
        mime_type = 'image/' + filepath.split('.')[-1].replace('jpg', 'jpeg')
    
    response = send_from_directory(swarascript_dir, filepath)
    response.headers['Content-Type'] = mime_type
    return response

# ============================================================================

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
    print("🎵 FLASK MUSIC TOOLS - COMBINED SERVER")
    print("="*70)
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"MEDIA_ROOT: {MEDIA_ROOT}")
    print("-"*70)
    print("📊 LIBRARY STATUS:")
    print(f"  FFmpeg: {FFMPEG_AVAILABLE}")
    print(f"  librosa (Carnatic): {LIBROSA_AVAILABLE}")
    print(f"  soundfile: {SOUNDFILE_AVAILABLE}")
    print(f"  speech_recognition: {SPEECH_RECOGNITION_AVAILABLE}")
    print("-"*70)
    print("🎯 AVAILABLE ENDPOINTS:")
    print("  Original:")
    print("    GET  /Kanakku.html")
    print("    GET  /api/songs")
    print("    POST /api/songs")
    print("    PUT  /api/songs/<id>")
    print("    GET  /api/test-swara/<filename>")
    print()
    print("  Carnatic Swara Recognition (NEW):")
    print("    POST /api/upload (audio file)")
    print("    GET  /api/test-file/<filename>")
    print()
    print("  File Serving:")
    print("    GET  /<filename>")
    print("="*70 + "\n")
    print("Starting server at http://127.0.0.1:5000")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    MIDI_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_json_file()
    app.run(host="127.0.0.1", port=5000, debug=False)
