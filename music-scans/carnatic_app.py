"""
Carnatic Swara Recognition - Simple, Fast, Direct
Focuses on transcribing S R G M P D N from audio
"""

import json
import os
from pathlib import Path
from flask import Flask, request, jsonify
import logging
import numpy as np

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

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

# Setup
BASE_DIR = Path(__file__).parent.absolute()
MEDIA_ROOT = BASE_DIR / "media"

app = Flask(__name__, static_folder=None)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS Headers
@app.before_request
def before_request():
    """Handle CORS preflight requests"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Carnatic swaras
SWARAS = ['s', 'r', 'g', 'm', 'p', 'd', 'n']
SWARA_NAMES = {
    's': 'Sa', 'r': 'Ri', 'g': 'Ga', 'm': 'Ma',
    'p': 'Pa', 'd': 'Dha', 'n': 'Ni'
}


def extract_swaras_from_text(text):
    """Extract swara characters from transcribed text
    Handles:
    - English pronunciations: sa, ra, ga, ma, pa, dha, ni
    - Tamil syllables: ச, ர, கா, மா, ப, த, ன
    - Short forms: s, r, g, m, p, d, n
    """
    text_lower = text.lower().strip()
    extracted = ''
    
    # Patterns that map to each swara (including Tamil variations)
    swara_mappings = {
        # Sa (ச)
        's': 's', 'sa': 's', 'saa': 's', 'shah': 's', 'sah': 's', 'sa:': 's', 'cha': 's',
        
        # Ri (ர)
        'r': 'r', 're': 'r', 'ree': 'r', 'ri': 'r', 'ray': 'r', 'rah': 'r', 're:': 'r',
        
        # Ga (கா)
        'g': 'g', 'ga': 'g', 'gaa': 'g', 'gah': 'g', 'ga:': 'g',
        
        # Ma (மா)
        'm': 'm', 'ma': 'm', 'maa': 'm', 'mah': 'm', 'ma:': 'm',
        
        # Pa (ப)
        'p': 'p', 'pa': 'p', 'paa': 'p', 'pah': 'p', 'pa:': 'p',
        
        # Dha (த)
        'd': 'd', 'da': 'd', 'dha': 'd', 'daa': 'd', 'dah': 'd', 'da:': 'd', 'tha': 'd',
        
        # Ni (ன)
        'n': 'n', 'na': 'n', 'ni': 'n', 'nee': 'n', 'nah': 'n', 'na:': 'n',
    }
    
    # Try longest patterns first to avoid partial matches
    for pattern in sorted(swara_mappings.keys(), key=len, reverse=True):
        if pattern in text_lower:
            swara = swara_mappings[pattern]
            # Replace this pattern with placeholder to avoid reprocessing
            text_lower = text_lower.replace(pattern, f'[{swara}]')
    
    # Extract the marked swaras
    for char in text_lower:
        if char in SWARAS:
            extracted += char
    
    return extracted


def transcribe_audio_chunk(audio_chunk, sr_rate=16000):
    """Transcribe a single audio chunk to get one swara"""
    if not SR_AVAILABLE:
        return None
    
    try:
        recognizer = sr.Recognizer()
        # Create AudioData from numpy array
        audio_bytes = (audio_chunk * 32767).astype(np.int16).tobytes()
        audio_data = sr.AudioData(audio_bytes, sr_rate, 2)
        
        # Transcribe
        text = recognizer.recognize_google(audio_data, language='en-US')
        logger.info(f"Transcribed chunk: {text}")
        
        # Extract single swara
        swara = extract_swaras_from_text(text)
        if swara:
            return swara[0]  # First swara found
        return None
    except sr.UnknownValueError:
        logger.debug("Could not understand audio chunk")
        return None
    except Exception as e:
        logger.debug(f"Transcription error: {e}")
        return None


def process_audio_with_chunks(audio_data, sr_rate=16000, chunk_duration=0.5):
    """Process audio in small chunks for swara recognition"""
    if not LIBROSA_AVAILABLE:
        return None, "librosa not available"
    
    try:
        # Settings for chunk processing
        chunk_samples = int(sr_rate * chunk_duration)
        swaras = []
        chunk_info = []
        
        logger.info(f"Processing audio: {len(audio_data)} samples at {sr_rate}Hz")
        logger.info(f"Chunk size: {chunk_samples} samples ({chunk_duration}s)")
        
        # Process each chunk
        num_chunks = (len(audio_data) + chunk_samples - 1) // chunk_samples
        logger.info(f"Total chunks: {num_chunks}")
        
        for i in range(num_chunks):
            start = i * chunk_samples
            end = min(start + chunk_samples, len(audio_data))
            chunk = audio_data[start:end]
            
            # Normalize chunk
            chunk_max = np.max(np.abs(chunk))
            if chunk_max > 0:
                chunk = chunk / chunk_max
            
            # Check if chunk has meaningful energy
            energy = np.sum(chunk ** 2) / len(chunk)
            logger.debug(f"Chunk {i}: energy={energy:.6f}")
            
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
                    logger.info(f"Chunk {i}: {swara}")
        
        return ''.join(swaras), chunk_info
        
    except Exception as e:
        logger.error(f"Chunk processing error: {e}")
        return None, str(e)


@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_and_recognize():
    """Upload audio and get swara notation"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided", "success": False}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({"error": "No file selected", "success": False}), 400
        
        # Read audio
        try:
            audio_data, sr_rate = librosa.load(file, sr=16000, mono=True)
            logger.info(f"Loaded audio: {len(audio_data)} samples at {sr_rate}Hz")
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            return jsonify({"error": f"Could not load audio: {str(e)}", "success": False}), 400
        
        # Process in chunks
        swaras, chunk_info = process_audio_with_chunks(audio_data, sr_rate, chunk_duration=0.5)
        
        if swaras is None:
            return jsonify({"error": chunk_info, "success": False}), 400
        
        logger.info(f"Final result: {swaras}")
        
        return jsonify({
            "swaras": swaras,
            "chunks": chunk_info,
            "success": True,
            "info": f"Recognized {len(swaras)} swaras in {len(chunk_info)} chunks"
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/api/test-file/<filename>', methods=['GET', 'OPTIONS'])
def test_file(filename):
    """Test with pre-recorded file from media folder"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Safety check
        file_path = MEDIA_ROOT / filename
        if not file_path.exists():
            return jsonify({"error": f"File not found: {filename}", "success": False}), 404
        
        logger.info(f"Testing with file: {filename}")
        
        # Load audio
        try:
            audio_data, sr_rate = librosa.load(str(file_path), sr=16000, mono=True)
            logger.info(f"Loaded {filename}: {len(audio_data)} samples at {sr_rate}Hz")
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return jsonify({"error": f"Could not load audio: {str(e)}", "success": False}), 400
        
        # Process in chunks
        swaras, chunk_info = process_audio_with_chunks(audio_data, sr_rate, chunk_duration=0.5)
        
        if swaras is None:
            return jsonify({"error": chunk_info, "success": False}), 400
        
        logger.info(f"Result for {filename}: {swaras}")
        
        return jsonify({
            "filename": filename,
            "swaras": swaras,
            "chunks": chunk_info,
            "success": True,
            "info": f"Recognized {len(swaras)} swaras"
        })
        
    except Exception as e:
        logger.error(f"Test file error: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/<path:filename>')
def serve_file(filename):
    """Serve HTML files"""
    file_path = BASE_DIR / filename
    if file_path.exists() and file_path.is_file():
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "File not found", 404


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎵 CARNATIC SWARA RECOGNITION")
    print("="*70)
    print(f"librosa: {LIBROSA_AVAILABLE}")
    print(f"soundfile: {SOUNDFILE_AVAILABLE}")
    print(f"speech_recognition: {SR_AVAILABLE}")
    print(f"Media folder: {MEDIA_ROOT}")
    print("="*70 + "\n")
    
    if not LIBROSA_AVAILABLE:
        print("⚠️  librosa not installed. Install with: pip install librosa")
    if not SR_AVAILABLE:
        print("⚠️  speech_recognition not installed. Install with: pip install SpeechRecognition pydub")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
