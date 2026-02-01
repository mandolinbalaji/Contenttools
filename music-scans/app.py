import json
import os
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response

# Everything lives here
BASE_DIR = Path(r"g:\My Drive\ContentTools\music-scans")
DATA_PATH = BASE_DIR / "songs.json"
LESSONS_DIR = BASE_DIR / "lessons"
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_DIR = BASE_DIR / "backups"

app = Flask(__name__, static_folder=None)
_write_lock = False  # single process guard


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


# BrahmaLayam API endpoints
@app.get("/api/lessons")
def get_lessons():
    """List all lessons"""
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    lessons = []
    for json_file in LESSONS_DIR.glob("*.json"):
        try:
            lesson_data = json.loads(json_file.read_text(encoding="utf-8"))
            lessons.append({
                "id": json_file.stem,
                "name": lesson_data.get("name", json_file.stem)
            })
        except:
            pass
    return jsonify(sorted(lessons, key=lambda x: x["name"]))


@app.get("/api/lesson/<lesson_id>")
def get_lesson(lesson_id):
    """Get a specific lesson"""
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    lesson_file = LESSONS_DIR / f"{lesson_id}.json"
    if not lesson_file.exists():
        return jsonify({"error": "Lesson not found"}), 404
    
    try:
        lesson_data = json.loads(lesson_file.read_text(encoding="utf-8"))
        return jsonify(lesson_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/lesson")
def save_lesson():
    """Create or update a lesson"""
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        lesson_data = request.json or {}
        lesson_id = lesson_data.get("id") or str(uuid.uuid4())
        
        # Validate required fields
        if not lesson_data.get("name"):
            lesson_data["name"] = f"Lesson {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        lesson_data["id"] = lesson_id
        lesson_file = LESSONS_DIR / f"{lesson_id}.json"
        lesson_file.write_text(json.dumps(lesson_data, indent=2), encoding="utf-8")
        
        return jsonify({"id": lesson_id, "status": "created"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.put("/api/lesson/<lesson_id>")
def update_lesson(lesson_id):
    """Update an existing lesson"""
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        lesson_data = request.json or {}
        lesson_file = LESSONS_DIR / f"{lesson_id}.json"
        
        lesson_data["id"] = lesson_id
        lesson_file.write_text(json.dumps(lesson_data, indent=2), encoding="utf-8")
        
        return jsonify({"id": lesson_id, "status": "updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.delete("/api/lesson/<lesson_id>")
def delete_lesson(lesson_id):
    """Delete a lesson"""
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    lesson_file = LESSONS_DIR / f"{lesson_id}.json"
    
    if not lesson_file.exists():
        return jsonify({"error": "Lesson not found"}), 404
    
    try:
        lesson_file.unlink()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


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


if __name__ == "__main__":
    print("Starting server at http://127.0.0.1:5000")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_json_file()
    app.run(host="127.0.0.1", port=5000, debug=False)
