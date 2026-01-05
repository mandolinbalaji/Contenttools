#!/usr/bin/env python3
"""
YouTube to MP3 Downloader
Downloads audio from YouTube URLs and saves as MP3.

Usage:
    python youtube_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID"

Requirements:
    pip install yt-dlp
"""

import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path

def download_youtube_audio(url, output_dir=None):
    """
    Download audio from YouTube URL and convert to MP3.

    Args:
        url (str): YouTube URL
        output_dir (str): Output directory (default: Downloads)

    Returns:
        dict: Result with success status and file path
    """
    if output_dir is None:
        # Use Downloads folder
        output_dir = Path.home() / "Downloads"
        output_dir.mkdir(exist_ok=True)

    try:
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            # yt-dlp command to download audio as MP3
            cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '128K',
                '--output', f'{temp_dir}/%(title)s.%(ext)s',
                '--no-playlist',
                '--quiet',
                '--progress',
                url
            ]

            # Run yt-dlp
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)

            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'yt-dlp failed: {result.stderr}'
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
                'yt-dlp',
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

def main():
    if len(sys.argv) != 2:
        print(json.dumps({
            'success': False,
            'error': 'Usage: python youtube_to_mp3.py "YOUTUBE_URL"'
        }))
        sys.exit(1)

    url = sys.argv[1]
    result = download_youtube_audio(url)

    print(json.dumps(result))

    if not result['success']:
        sys.exit(1)

if __name__ == '__main__':
    main()</content>
<parameter name="filePath">c:\AnytuneToLRC\youtube_to_mp3.py