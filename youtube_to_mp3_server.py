#!/usr/bin/env python3
"""
YouTube to MP3 Web Server
Provides a web interface for downloading YouTube audio as MP3.

Usage:
    python youtube_to_mp3_server.py

Then open http://localhost:5000 in your browser.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import subprocess
import tempfile
from pathlib import Path
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def download_youtube_audio(url):
    """
    Download audio from YouTube URL and convert to MP3.

    Args:
        url (str): YouTube URL

    Returns:
        dict: Result with success status and file path
    """
    output_dir = Path.home() / "Downloads"
    output_dir.mkdir(exist_ok=True)

    try:
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            # yt-dlp command to download audio as MP3
            cmd = [
                'python', '-m', 'yt_dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '128K',
                '--output', f'{temp_dir}/%(title)s.%(ext)s',
                '--no-playlist',
                '--format', 'bestaudio/best',
                '--ignore-errors',
                '--no-warnings',
                url
            ]

            # Run yt-dlp
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or 'Unknown yt-dlp error'
                return {
                    'success': False,
                    'error': f'yt-dlp failed: {error_msg}'
                }

            # Find the downloaded file
            downloaded_files = list(Path(temp_dir).glob('*.mp3'))
            if not downloaded_files:
                return {
                    'success': False,
                    'error': 'No MP3 file was created'
                }

            downloaded_file = downloaded_files[0]

            # Get video info for filename
            info_cmd = [
                'python', '-m', 'yt_dlp',
                '--print', '%(title)s',
                '--no-playlist',
                '--quiet',
                url
            ]

            info_result = subprocess.run(info_cmd, capture_output=True, text=True)
            title = info_result.stdout.strip() if info_result.returncode == 0 else 'youtube_audio'

            # Clean filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_title:
                safe_title = 'youtube_audio'

            final_filename = f"{safe_title}.mp3"
            final_path = output_dir / final_filename

            # Handle duplicate filenames
            counter = 1
            while final_path.exists():
                name_without_ext = final_path.stem
                final_filename = f"{name_without_ext}_{counter}.mp3"
                final_path = output_dir / final_filename
                counter += 1

            # Move file to final location
            import shutil
            shutil.move(str(downloaded_file), str(final_path))

            return {
                'success': True,
                'file_path': str(final_path),
                'filename': final_filename,
                'title': title
            }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error: {str(e)}'
        }

@app.route('/')
def index():
    return send_file('youtube-to-mp3.html')

@app.route('/api/status', methods=['GET'])
def status():
    """Return server status."""
    return jsonify({
        'status': 'running',
        'message': 'YouTube to MP3 server is online',
        'version': '1.0'
    })

@app.route('/api/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'})

        # Validate URL format
        if not ('youtube.com' in url or 'youtu.be' in url):
            return jsonify({'success': False, 'error': 'Invalid YouTube URL'})

        # Download in background thread to avoid blocking
        result = download_youtube_audio(url)

        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Successfully downloaded: {result["filename"]}',
                'filename': result['filename'],
                'title': result['title']
            })
        else:
            return jsonify({'success': False, 'error': result['error']})

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

if __name__ == '__main__':
    print("Starting YouTube to MP3 server...")
    print("Open http://localhost:7773 in your browser")
    print("Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=7773)