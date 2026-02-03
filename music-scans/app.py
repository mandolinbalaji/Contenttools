import json
import os
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response

# Everything lives here - use the directory where this script is located
# This ensures it works regardless of where the batch file is run from
BASE_DIR = Path(__file__).parent.absolute()
print(f"[STARTUP] BASE_DIR: {BASE_DIR}")
print(f"[STARTUP] Script location: {Path(__file__).absolute()}")

DATA_PATH = BASE_DIR / "songs.json"
LESSONS_DIR = BASE_DIR / "lessons"
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_DIR = BASE_DIR / "backups"

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


@app.get("/brahmalayam.html")
def brahmalayam():
    """Serve BrahmaLayam editor"""
    brahmalayam_file = BASE_DIR / "brahmalayam.html"
    if not brahmalayam_file.exists():
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(BASE_DIR, "brahmalayam.html")


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


# BrahmaLayam API endpoints - using lessons directory

@app.post("/api/save")
def save_to_file():
    """Golden Rule: Save lesson to /data/ folder"""
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        lesson_data = request.json or {}
        lesson_id = lesson_data.get("id") or str(uuid.uuid4())
        
        lesson_file = DATA_DIR / f"{lesson_id}.json"
        lesson_file.write_text(json.dumps(lesson_data, indent=2), encoding="utf-8")
        
        return jsonify({"id": lesson_id, "status": "saved", "path": str(lesson_file)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/export")
def export_to_musicxml():
    """Golden Rule: Convert JSON lesson to MusicXML format for MuseScore compatibility"""
    try:
        lesson_data = request.json or {}
        atomic_notes = lesson_data.get("atomicNotes", [])
        metadata = lesson_data.get("metadata", {})
        
        if not atomic_notes:
            return jsonify({"error": "No notes to export"}), 400
        
        # Map Carnatic notes to Western notation
        note_map = {
            'S': 'D', 'R': 'E', 'G': 'F#', 'M': 'G',
            'P': 'A', 'D': 'B', 'N': 'C'
        }
        
        # Build MusicXML structure
        musicxml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/partwise.dtd">
<score-partwise version="4.0">
  <work>
    <work-title>Carnatic Lesson Export</work-title>
  </work>
  <identification>
    <creator type="software">BrahmaLayam</creator>
  </identification>
  <defaults>
    <scaling>
      <millimeters>7.05</millimeters>
      <tenths>40</tenths>
    </scaling>
  </defaults>
  <part-list>
    <score-part id="P1">
      <part-name>Carnatic Notation</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <clef>
          <sign>treble</sign>
          <line>2</line>
        </clef>
      </attributes>
'''
        
        # Add notes
        for note in atomic_notes[:32]:  # Limit to 32 notes per measure
            char = note.get('char', 'S')
            western_note = note_map.get(char, 'D')
            octave = 4 + note.get('octave', 0)
            duration = 2 if note.get('speed', 1) == 2 else 4  # Double speed = half duration
            
            musicxml += f'''      <note>
        <pitch>
          <step>{western_note[0]}</step>
          <octave>{octave}</octave>
        </pitch>
        <duration>{duration}</duration>
        <type>{'eighth' if duration == 2 else 'quarter'}</type>
      </note>
'''
        
        musicxml += '''    </measure>
  </part>
</score-partwise>'''
        
        return musicxml, 200, {'Content-Type': 'application/xml', 'Content-Disposition': 'attachment;filename=lesson.musicxml'}
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Lessons API endpoints - read/write to single lessons.json file
LESSONS_FILE = BASE_DIR / "lessons.json"
print(f"[STARTUP] LESSONS_FILE: {LESSONS_FILE}")
print(f"[STARTUP] LESSONS_FILE exists: {LESSONS_FILE.exists()}")

def _load_lessons():
    """Load all lessons from lessons.json"""
    try:
        print(f"DEBUG: Loading lessons from: {LESSONS_FILE}", flush=True)
    except:
        pass
    
    if not LESSONS_FILE.exists():
        try:
            print("DEBUG: lessons.json does not exist, returning empty list", flush=True)
        except:
            pass
        return []
    try:
        content = LESSONS_FILE.read_text(encoding="utf-8").strip()
        try:
            print(f"DEBUG: File content length: {len(content)} characters", flush=True)
        except:
            pass
        if not content:
            try:
                print("DEBUG: File is empty", flush=True)
            except:
                pass
            return []
        data = json.loads(content)
        # Handle both old array format and new object format with thala-beats
        if isinstance(data, dict) and "lessons" in data:
            data = data.get("lessons", [])
        try:
            print(f"DEBUG: Loaded {len(data)} lessons", flush=True)
        except:
            pass
        return data
    except Exception as e:
        try:
            print(f"ERROR loading lessons: {e}", flush=True)
        except:
            import sys
            sys.stderr.write(f"ERROR loading lessons: {str(e)}\n")
        return []

def _save_lessons(lessons):
    """Save lessons to lessons.json, preserving thala-beats if present"""
    try:
        # Check if existing file has thala-beats data
        thala_beats = None
        if LESSONS_FILE.exists():
            try:
                existing = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
                if isinstance(existing, dict) and "thala-beats" in existing:
                    thala_beats = existing["thala-beats"]
            except:
                pass
        
        # Build output structure
        output = {"lessons": lessons}
        if thala_beats:
            output["thala-beats"] = thala_beats
        
        LESSONS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Error saving lessons: {e}")

@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    """Get all lessons - returns just the lessons array"""
    print("\n" + "="*70, flush=True)
    print("[ENDPOINT CALLED] GET /api/lessons", flush=True)
    
    try:
        file_path = Path(__file__).parent / "lessons.json"
        print(f"[ENDPOINT] Reading from: {file_path}", flush=True)
        print(f"[ENDPOINT] File exists: {file_path.exists()}", flush=True)
        
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8').strip()
            print(f"[ENDPOINT] File content length: {len(content)}", flush=True)
            data = json.loads(content)
            
            # Extract lessons array from the new format
            if isinstance(data, dict) and "lessons" in data:
                lessons = data["lessons"]
            else:
                lessons = data if isinstance(data, list) else []
            
            print(f"[ENDPOINT] Returning {len(lessons)} lessons", flush=True)
            return jsonify(lessons), 200
        else:
            print(f"[ENDPOINT] File NOT found!", flush=True)
            return jsonify([]), 200
    except Exception as e:
        print(f"[ENDPOINT] ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify([]), 200
    finally:
        print("="*70, flush=True)

@app.route('/api/lesson/<lesson_id>', methods=['GET'])
def get_lesson(lesson_id):
    """Get a specific lesson"""
    lessons = _load_lessons()
    for lesson in lessons:
        if lesson.get('id') == lesson_id:
            return jsonify(lesson)
    return jsonify({"error": "Lesson not found"}), 404

@app.route('/api/thala-beats', methods=['GET'])
def get_thala_beats():
    """Get thala-beats from lessons.json"""
    try:
        if not LESSONS_FILE.exists():
            return jsonify({"error": "Data file not found"}), 404
        
        content = LESSONS_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return jsonify({"error": "Data file is empty"}), 404
        
        data = json.loads(content)
        # Handle both old array format and new object format
        if isinstance(data, dict) and "thala-beats" in data:
            return jsonify(data["thala-beats"]), 200
        else:
            return jsonify({"error": "Thala-beats data not found"}), 404
    except Exception as e:
        print(f"Error loading thala-beats: {e}", flush=True)
        return jsonify({"error": "Error loading thala beats"}), 500

@app.route('/api/lesson', methods=['POST'])
def create_lesson():
    """Create a new lesson"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Ensure ID
    if 'id' not in data or not data['id']:
        data['id'] = str(uuid.uuid4())
    
    # Ensure timestamp
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    
    lessons = _load_lessons()
    lessons.append(data)
    _save_lessons(lessons)
    
    return jsonify(data), 201

@app.route('/api/lesson/<lesson_id>', methods=['PUT'])
def update_lesson(lesson_id):
    """Update an existing lesson"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    lessons = _load_lessons()
    for i, lesson in enumerate(lessons):
        if lesson.get('id') == lesson_id:
            data['id'] = lesson_id  # Preserve ID
            data['timestamp'] = lesson.get('timestamp', datetime.now().isoformat())  # Preserve original timestamp
            data['updatedAt'] = datetime.now().isoformat()
            lessons[i] = data
            _save_lessons(lessons)
            return jsonify(data)
    
    return jsonify({"error": "Lesson not found"}), 404

@app.route('/api/lesson/<lesson_id>', methods=['DELETE'])
def delete_lesson(lesson_id):
    """Delete a lesson"""
    lessons = _load_lessons()
    lessons = [l for l in lessons if l.get('id') != lesson_id]
    _save_lessons(lessons)
    return jsonify({"success": True})


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


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FLASK APP INITIALIZATION")
    print("="*70)
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"LESSONS_FILE: {LESSONS_FILE}")
    print(f"LESSONS_FILE exists: {LESSONS_FILE.exists()}")
    
    # Test loading lessons
    test_lessons = _load_lessons()
    print(f"Test load: Got {len(test_lessons)} lessons")
    if test_lessons:
        print(f"First lesson: {test_lessons[0].get('name', 'Unknown')}")
    
    print("="*70 + "\n")
    print("Starting server at http://127.0.0.1:5000")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_json_file()
    app.run(host="127.0.0.1", port=5000, debug=False)
