#!/usr/bin/env python3
"""
YouTube Shorts Video Generator
Generates MP4 videos with lyrics/notation overlay from CSLP files.

Usage:
    python generate_video.py <audio_file> <cslp_file> [options]

Options:
    --title "Title"       Video title (default: from CSLP metadata)
    --info "Info text"    Scrolling info text (optional)
    --output output.mp4   Output filename (default: auto from title)

Requirements:
    pip install pillow
    FFmpeg must be installed and in PATH
"""

import json
import sys
import os
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow is required. Install with: pip install pillow")
    sys.exit(1)

# Video constants
WIDTH = 1080
HEIGHT = 1920
FPS = 30
TITLE_HEIGHT = 150
STRIP_HEIGHT = 400
INFO_HEIGHT = 60
CHROMA_KEY = (0, 255, 0)  # Green screen

def check_ffmpeg():
    """Check if FFmpeg is available."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def load_cslp(cslp_path):
    """Load and parse CSLP file."""
    with open(cslp_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_font(size, bold=False):
    """Get a font, falling back to default if needed."""
    font_names = [
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
    ]
    
    for font_path in font_names:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                pass
    
    # Fallback to default
    return ImageFont.load_default()

def get_entry_at_time(timeline, current_time):
    """Find the timeline entry for the current time."""
    current_entry = {'text': '', 'notation': ''}
    
    for entry in reversed(timeline):
        if entry and 'time' in entry and current_time >= entry['time']:
            current_entry = {
                'text': str(entry.get('text', '') or '').strip(),
                'notation': str(entry.get('notation', '') or '').strip()
            }
            break
    
    return current_entry

def draw_frame(current_time, timeline, title, info_text):
    """Draw a single frame and return as PIL Image."""
    img = Image.new('RGB', (WIDTH, HEIGHT), CHROMA_KEY)
    draw = ImageDraw.Draw(img)
    
    # Fonts
    title_font = get_font(64, bold=True)
    lyrics_font = get_font(48, bold=True)
    notation_font = get_font(40)
    info_font = get_font(28)
    
    # Draw title area (if title provided)
    if title:
        draw.rectangle([0, 0, WIDTH, TITLE_HEIGHT], fill=(51, 51, 51))
        title_upper = title.upper()
        bbox = draw.textbbox((0, 0), title_upper, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        y = (TITLE_HEIGHT - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), title_upper, fill=(255, 255, 255), font=title_font)
    
    # Get current entry
    entry = get_entry_at_time(timeline, current_time)
    
    # Calculate strip position
    strip_y = HEIGHT - STRIP_HEIGHT
    
    # Draw info bar (if info text provided)
    if info_text:
        info_y = strip_y - INFO_HEIGHT
        draw.rectangle([0, info_y, WIDTH, strip_y], fill=(245, 245, 245))
        
        # Marquee effect
        bbox = draw.textbbox((0, 0), info_text, font=info_font)
        text_width = bbox[2] - bbox[0]
        gap = 100
        total_width = text_width + gap
        scroll_speed = 80
        scroll_offset = (current_time * scroll_speed) % total_width
        
        # Draw scrolling text
        x = WIDTH - scroll_offset
        while x < WIDTH + text_width:
            draw.text((x, info_y + (INFO_HEIGHT - 28) // 2), info_text, 
                     fill=(102, 102, 102), font=info_font)
            x += total_width
    
    # Draw bottom strip (white background)
    draw.rectangle([0, strip_y, WIDTH, HEIGHT], fill=(255, 255, 255))
    
    # Draw lyrics
    lyrics_text = entry['text']
    if lyrics_text:
        bbox = draw.textbbox((0, 0), lyrics_text, font=lyrics_font)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        y = strip_y + STRIP_HEIGHT // 3 - 24
        draw.text((x, y), lyrics_text, fill=(0, 0, 0), font=lyrics_font)
    
    # Draw notation
    notation_text = entry['notation']
    if notation_text:
        bbox = draw.textbbox((0, 0), notation_text, font=notation_font)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        y = strip_y + (STRIP_HEIGHT * 2 // 3) - 20
        draw.text((x, y), notation_text, fill=(51, 51, 51), font=notation_font)
    
    return img

def get_audio_duration(audio_path):
    """Get audio duration using FFprobe."""
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())

def generate_video(audio_path, cslp_path, title=None, info_text=None, output_path=None):
    """Generate the video using FFmpeg."""
    
    # Check FFmpeg
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed or not in PATH")
        print("Download from: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    # Load CSLP
    print(f"Loading CSLP: {cslp_path}")
    cslp = load_cslp(cslp_path)
    timeline = cslp.get('data', {}).get('timeline', [])
    
    # Get title from args or CSLP
    if not title:
        title = cslp.get('metadata', {}).get('title', '')
    
    # Get audio duration
    print(f"Loading audio: {audio_path}")
    duration = get_audio_duration(audio_path)
    total_frames = int(duration * FPS)
    print(f"Duration: {duration:.2f}s, Frames: {total_frames}")
    
    # Output path
    if not output_path:
        safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in (title or 'video'))
        output_path = f"{safe_title}_shorts.mp4"
    
    # Create temp directory for frames
    temp_dir = tempfile.mkdtemp(prefix='video_gen_')
    print(f"Generating frames in: {temp_dir}")
    
    try:
        # Generate frames
        for frame_num in range(total_frames):
            current_time = frame_num / FPS
            
            # Progress
            if frame_num % 30 == 0:
                progress = (frame_num / total_frames) * 100
                print(f"\rGenerating frames: {progress:.1f}% ({frame_num}/{total_frames})", end='', flush=True)
            
            # Draw frame
            img = draw_frame(current_time, timeline, title, info_text)
            
            # Save frame
            frame_path = os.path.join(temp_dir, f"frame_{frame_num:06d}.png")
            img.save(frame_path, 'PNG')
        
        print(f"\rGenerating frames: 100% ({total_frames}/{total_frames})")
        
        # Combine frames with audio using FFmpeg
        print(f"Encoding video: {output_path}")
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(FPS),
            '-i', os.path.join(temp_dir, 'frame_%06d.png'),
            '-i', audio_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            output_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True)
        
        print(f"\n✓ Video saved: {output_path}")
        print(f"  Resolution: {WIDTH}x{HEIGHT}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Format: MP4 (H.264 + AAC) - YouTube ready!")
        
    finally:
        # Cleanup temp directory
        print("Cleaning up temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(
        description='Generate YouTube Shorts video from CSLP and audio files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate_video.py song.mp3 song.cslp
    python generate_video.py song.mp3 song.cslp --title "My Song"
    python generate_video.py song.mp3 song.cslp --title "My Song" --info "Raga: Shankarabharanam"
    python generate_video.py song.mp3 song.cslp --output my_video.mp4
        """
    )
    
    parser.add_argument('audio', help='Audio file (MP3, WAV, etc.)')
    parser.add_argument('cslp', help='CSLP file with timeline data')
    parser.add_argument('--title', help='Video title (default: from CSLP metadata)')
    parser.add_argument('--info', help='Scrolling info text (optional)')
    parser.add_argument('--output', '-o', help='Output filename (default: auto from title)')
    
    args = parser.parse_args()
    
    # Validate files exist
    if not os.path.exists(args.audio):
        print(f"Error: Audio file not found: {args.audio}")
        sys.exit(1)
    
    if not os.path.exists(args.cslp):
        print(f"Error: CSLP file not found: {args.cslp}")
        sys.exit(1)
    
    generate_video(args.audio, args.cslp, args.title, args.info, args.output)

if __name__ == '__main__':
    main()
