#!/usr/bin/env python3
"""
Precision Looping Audio Player - Phase 2
Sample-accurate playback with CSLP markers and lyrics display.

Features:
- Load audio file (MP3, WAV, FLAC, etc.)
- Load CSLP file with markers and lyrics
- Play/Pause/Stop with sample-accurate positioning
- Select audio output device
- Waveform visualization with playhead
- Clickable markers from CSLP
- Lyrics/notation display synced to playback
- Click to seek
- Keyboard shortcuts
"""

import sys
import json
import numpy as np
import sounddevice as sd
import soundfile as sf
import threading
from pathlib import Path
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QSlider, QFrame,
    QSplitter, QGroupBox, QScrollArea, QCheckBox, QSpinBox,
    QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QKeySequence, QShortcut, QFont, QPixmap
from project_manager import ProjectManager
from project_dialog import ProjectDialog


class AudioEngine(QObject):
    """Core audio engine with sample-accurate playback."""
    
    position_changed = pyqtSignal(int)  # Emits current sample position
    playback_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.audio_data = None  # numpy array of audio samples
        self.sample_rate = 44100
        self.channels = 2
        self.position = 0  # Current sample position
        self.is_playing = False
        self.stream = None
        self.device = None
        
        # Loop points (in samples)
        self.loop_enabled = False
        self.loop_start = 0
        self.loop_end = 0
        
        # Thread safety
        self.lock = threading.Lock()
        
    def load_file(self, filepath):
        """Load audio file into memory."""
        try:
            # Read entire file into memory
            data, sr = sf.read(filepath, dtype='float32')
            
            # Convert mono to stereo if needed
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            
            with self.lock:
                self.audio_data = data
                self.sample_rate = sr
                self.channels = data.shape[1] if len(data.shape) > 1 else 1
                self.position = 0
                self.loop_start = 0
                self.loop_end = len(data)
            
            return True, f"Loaded: {len(data)} samples, {sr}Hz, {self.channels}ch"
        except Exception as e:
            return False, str(e)
    
    def get_duration(self):
        """Get duration in seconds."""
        if self.audio_data is None:
            return 0
        return len(self.audio_data) / self.sample_rate
    
    def get_position_seconds(self):
        """Get current position in seconds."""
        return self.position / self.sample_rate
    
    def set_position_seconds(self, seconds):
        """Set position in seconds."""
        with self.lock:
            self.position = int(seconds * self.sample_rate)
            if self.audio_data is not None:
                self.position = max(0, min(self.position, len(self.audio_data) - 1))
    
    def set_position_samples(self, samples):
        """Set position in samples."""
        with self.lock:
            self.position = int(samples)
            if self.audio_data is not None:
                self.position = max(0, min(self.position, len(self.audio_data) - 1))
    
    def set_device(self, device_index):
        """Set output device."""
        self.device = device_index
        # If playing, restart stream with new device
        if self.is_playing:
            self.stop()
            self.play()
    
    def _audio_callback(self, outdata, frames, time, status):
        """Audio callback - called by sounddevice to fill output buffer."""
        if status:
            print(f"Audio status: {status}")
        
        with self.lock:
            if self.audio_data is None or not self.is_playing:
                outdata.fill(0)
                return
            
            # Calculate end position for this buffer
            end_pos = self.position + frames
            
            # Handle looping
            if self.loop_enabled:
                # Ensure position is within loop bounds
                if self.position >= self.loop_end or self.position < self.loop_start:
                    self.position = self.loop_start
                
                # Calculate how many samples until loop end
                samples_before_loop = self.loop_end - self.position
                
                if samples_before_loop <= 0:
                    # Already at or past loop end, jump to start
                    self.position = self.loop_start
                    samples_before_loop = self.loop_end - self.position
                
                if samples_before_loop >= frames:
                    # Entire buffer fits before loop end
                    end_pos = self.position + frames
                    outdata[:] = self.audio_data[self.position:end_pos]
                    self.position = end_pos
                else:
                    # Need to wrap around
                    samples_after_loop = frames - samples_before_loop
                    
                    if samples_before_loop > 0:
                        outdata[:samples_before_loop] = self.audio_data[self.position:self.loop_end]
                    
                    # Wrap to loop start
                    self.position = self.loop_start
                    
                    # Fill remaining samples, possibly multiple loops if loop is tiny
                    loop_length = self.loop_end - self.loop_start
                    if loop_length > 0 and samples_after_loop > 0:
                        remaining = samples_after_loop
                        write_pos = samples_before_loop
                        
                        while remaining > 0:
                            chunk = min(remaining, loop_length)
                            outdata[write_pos:write_pos + chunk] = self.audio_data[self.loop_start:self.loop_start + chunk]
                            write_pos += chunk
                            remaining -= chunk
                        
                        self.position = self.loop_start + (samples_after_loop % loop_length)
                    else:
                        # Loop is invalid, just fill with zeros
                        outdata[samples_before_loop:] = 0
            else:
                # Normal playback
                if end_pos <= len(self.audio_data):
                    outdata[:] = self.audio_data[self.position:end_pos]
                    self.position = end_pos
                else:
                    # End of file
                    remaining = len(self.audio_data) - self.position
                    if remaining > 0:
                        outdata[:remaining] = self.audio_data[self.position:]
                        outdata[remaining:] = 0
                    else:
                        outdata.fill(0)
                    self.position = len(self.audio_data)
                    self.is_playing = False
    
    def play(self):
        """Start playback."""
        if self.audio_data is None:
            return False
        
        if self.is_playing:
            return True
        
        try:
            self.is_playing = True
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                device=self.device,
                blocksize=512,  # Low latency
                latency='low'
            )
            self.stream.start()
            return True
        except Exception as e:
            print(f"Playback error: {e}")
            self.is_playing = False
            return False
    
    def pause(self):
        """Pause playback."""
        self.is_playing = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
    
    def stop(self):
        """Stop playback and reset position."""
        self.pause()
        with self.lock:
            self.position = self.loop_start if self.loop_enabled else 0
    
    def toggle_play(self):
        """Toggle play/pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()
        return self.is_playing
    
    def set_loop(self, enabled, start_samples=None, end_samples=None):
        """Set loop points."""
        with self.lock:
            self.loop_enabled = enabled
            if start_samples is not None:
                self.loop_start = int(start_samples)
            if end_samples is not None:
                self.loop_end = int(end_samples)
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()


class Track:
    """Represents a single audio track with its own output device."""
    
    def __init__(self, track_id, name="Track"):
        self.id = track_id
        self.name = name
        self.audio_data = None
        self.sample_rate = 44100
        self.channels = 2
        self.volume = 1.0  # 0.0 to 2.0 (200%)
        self.muted = False
        self.solo = False
        self.device = None  # Output device index
        self.filepath = None
        self.stream = None  # Each track has its own output stream
    
    def load_file(self, filepath):
        """Load audio file for this track."""
        try:
            data, sr = sf.read(filepath, dtype='float32')
            
            # Convert mono to stereo
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            
            self.audio_data = data
            self.sample_rate = sr
            self.channels = data.shape[1] if len(data.shape) > 1 else 1
            self.filepath = filepath
            self.name = Path(filepath).stem
            
            return True, f"Loaded: {len(data)} samples"
        except Exception as e:
            return False, str(e)
    
    def get_samples(self, start, count, has_solo=False):
        """Get audio samples with volume applied."""
        if self.audio_data is None:
            return np.zeros((count, 2), dtype='float32')
        
        end = min(start + count, len(self.audio_data))
        if start >= len(self.audio_data):
            return np.zeros((count, 2), dtype='float32')
        
        samples = self.audio_data[start:end].copy()
        
        # Check if should be silent
        if self.muted or (has_solo and not self.solo):
            samples *= 0
        else:
            samples *= self.volume
        
        # Pad if needed
        if len(samples) < count:
            padding = np.zeros((count - len(samples), samples.shape[1]), dtype='float32')
            samples = np.vstack((samples, padding))
        
        return samples
    
    def set_device(self, device_index):
        """Set output device for this track."""
        self.device = device_index
    
    def cleanup(self):
        """Clean up stream."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None


class MultiTrackEngine(QObject):
    """Engine that manages multiple tracks with per-track output devices.
    
    Uses blocking write approach for cleaner multi-device output.
    """
    
    position_changed = pyqtSignal(int)
    playback_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.tracks = []  # List of Track objects
        self.sample_rate = 44100
        self.position = 0  # Current position in samples
        self.is_playing = False
        self.streams = {}  # device_index -> stream
        self._playback_thread = None
        self._stop_event = threading.Event()
        
        # Loop
        self.loop_enabled = False
        self.loop_start = 0
        self.loop_end = 0
        
        self.lock = threading.Lock()
        self._next_track_id = 1
    
    def add_track(self, filepath=None):
        """Add a new track."""
        track_id = self._next_track_id
        self._next_track_id += 1
        track = Track(track_id, f"Track {track_id}")
        
        if filepath:
            success, msg = track.load_file(filepath)
            if success:
                # Update engine sample rate from first track
                if not self.tracks:
                    self.sample_rate = track.sample_rate
                    self.loop_end = len(track.audio_data)
        
        self.tracks.append(track)
        return track
    
    def remove_track(self, track_id):
        """Remove a track by ID."""
        # Find and cleanup the track
        for t in self.tracks:
            if t.id == track_id:
                t.cleanup()
                break
        self.tracks = [t for t in self.tracks if t.id != track_id]
        
        # Rebuild streams if playing
        if self.is_playing:
            self._rebuild_streams()
    
    def _rebuild_streams(self):
        """Rebuild audio streams after track changes during playback."""
        if not self.is_playing:
            return
        
        # Pause to stop current playback and close streams
        self.pause()
        
        # Restart playback with new stream configuration
        self.play()
    
    def get_total_samples(self):
        """Get max samples across all tracks."""
        if not self.tracks:
            return 0
        return max((len(t.audio_data) if t.audio_data is not None else 0) for t in self.tracks)
    
    def get_duration(self):
        """Get max duration across all tracks."""
        return self.get_total_samples() / self.sample_rate
    
    def get_position_seconds(self):
        """Get current position in seconds."""
        return self.position / self.sample_rate
    
    def set_position_samples(self, samples):
        """Set position in samples."""
        with self.lock:
            self.position = int(samples)
    
    def _has_solo(self):
        """Check if any track is soloed."""
        return any(t.solo for t in self.tracks)
    
    def _get_tracks_by_device(self):
        """Group tracks by their output device."""
        device_tracks = {}
        for track in self.tracks:
            device = track.device  # None means default device
            if device not in device_tracks:
                device_tracks[device] = []
            device_tracks[device].append(track)
        return device_tracks
    
    def _playback_loop(self):
        """Main playback loop running in separate thread - blocking writes."""
        BLOCK_SIZE = 1024  # Samples per write
        
        while not self._stop_event.is_set() and self.is_playing:
            with self.lock:
                current_pos = self.position
                
                # Handle looping
                if self.loop_enabled:
                    if current_pos >= self.loop_end:
                        current_pos = self.loop_start
                        self.position = current_pos
                    elif current_pos < self.loop_start:
                        current_pos = self.loop_start
                        self.position = current_pos
                
                # Check for end of tracks
                max_len = self.get_total_samples()
                if current_pos >= max_len and not self.loop_enabled:
                    self.is_playing = False
                    break
                
                has_solo = self._has_solo()
                
                # Generate audio for each device
                for device_index, stream in list(self.streams.items()):
                    device_tracks = [t for t in self.tracks if t.device == device_index]
                    
                    # Mix tracks for this device
                    mixed = np.zeros((BLOCK_SIZE, 2), dtype='float32')
                    for track in device_tracks:
                        if track.audio_data is None:
                            continue
                        samples = track.get_samples(current_pos, BLOCK_SIZE, has_solo)
                        mixed += samples
                    
                    # Clip and write to stream
                    try:
                        stream.write(np.clip(mixed, -1.0, 1.0))
                    except Exception as e:
                        print(f"Write error: {e}")
                
                # Advance position
                self.position = current_pos + BLOCK_SIZE
    
    def _generate_metronome_click(self):
        """Generate a single metronome click sound."""
        # Create a click sound exactly BLOCK_SIZE long
        block_size = 1024
        duration_seconds = block_size / self.sample_rate
        t = np.linspace(0, duration_seconds, block_size, False)
        
        # Simple sine wave click with exponential decay
        frequency = 1000  # 1kHz click
        click = np.sin(2 * np.pi * frequency * t) * np.exp(-t * 200)  # Fast decay
        
        # Convert to stereo
        return np.column_stack((click, click)).astype('float32')
    
    def play_with_countin(self, bpm, beats):
        """Start playback with metronome count-in."""
        if not self.tracks:
            return False
        
        if self.is_playing:
            return True
        
        try:
            # Store count-in settings
            self.countin_bpm = bpm
            self.countin_beats = beats
            self.countin_click_samples = self._generate_metronome_click()
            self.countin_silence_samples = np.zeros((1024, 2), dtype='float32')  # Silence block
            self.countin_current_beat = 0
            self.countin_next_click_time = 0  # Will be set when playback starts
            
            # Reset position for count-in
            self.position = 0
            
            # Get unique devices
            device_tracks = self._get_tracks_by_device()
            
            # Create blocking output streams for each device
            for device_index in device_tracks.keys():
                try:
                    stream = sd.OutputStream(
                        samplerate=self.sample_rate,
                        channels=2,
                        device=device_index,
                        blocksize=1024,
                        latency='low'
                    )
                    stream.start()
                    self.streams[device_index] = stream
                except Exception as e:
                    print(f"Error creating stream for device {device_index}: {e}")
            
            # Start playback
            self._stop_event.clear()
            self.is_playing = True
            
            # Start playback thread with count-in
            self._playback_thread = threading.Thread(target=self._countin_playback_loop, daemon=True)
            self._playback_thread.start()
            
            return True
        except Exception as e:
            print(f"Count-in playback error: {e}")
            self.is_playing = False
            return False
    
    def _countin_playback_loop(self):
        """Playback loop with metronome count-in."""
        BLOCK_SIZE = 1024
        click_interval_samples = int((60.0 / self.countin_bpm) * self.sample_rate)
        
        while not self._stop_event.is_set() and self.is_playing:
            with self.lock:
                current_pos = self.position
                
                # Handle count-in phase
                if self.countin_current_beat < self.countin_beats:
                    # Check if it's time for next click
                    if current_pos >= self.countin_next_click_time:
                        # Play click on all devices
                        for device_index, stream in list(self.streams.items()):
                            try:
                                stream.write(self.countin_click_samples)
                            except Exception as e:
                                print(f"Count-in write error: {e}")
                        
                        self.countin_current_beat += 1
                        self.countin_next_click_time += click_interval_samples
                        
                        # Signal UI to update beat counter
                        self.position_changed.emit(self.countin_current_beat)
                    else:
                        # Write silence on all devices
                        for device_index, stream in list(self.streams.items()):
                            try:
                                stream.write(self.countin_silence_samples)
                            except Exception as e:
                                print(f"Count-in silence write error: {e}")
                    
                    # Advance position
                    self.position = current_pos + BLOCK_SIZE
                    continue
                
                # Count-in finished, switch to normal playback
                elif self.countin_current_beat == self.countin_beats:
                    # Reset position to start for normal playback
                    self.position = self.loop_start if self.loop_enabled else 0
                    current_pos = self.position
                    self.countin_current_beat += 1  # Mark as finished
                
                # Normal playback logic (same as _playback_loop)
                # Handle looping
                if self.loop_enabled:
                    if current_pos >= self.loop_end:
                        current_pos = self.loop_start
                        self.position = current_pos
                    elif current_pos < self.loop_start:
                        current_pos = self.loop_start
                        self.position = current_pos
                
                # Check for end of tracks
                max_len = self.get_total_samples()
                if current_pos >= max_len and not self.loop_enabled:
                    self.is_playing = False
                    break
                
                has_solo = self._has_solo()
                
                # Generate audio for each device
                for device_index, stream in list(self.streams.items()):
                    device_tracks = [t for t in self.tracks if t.device == device_index]
                    
                    # Mix tracks for this device
                    mixed = np.zeros((BLOCK_SIZE, 2), dtype='float32')
                    for track in device_tracks:
                        if track.audio_data is not None:
                            samples = track.get_samples(current_pos, BLOCK_SIZE, has_solo)
                            mixed += samples
                    
                    # Clip and write to stream
                    try:
                        stream.write(np.clip(mixed, -1.0, 1.0))
                    except Exception as e:
                        print(f"Write error: {e}")
                
                # Advance position
                self.position = current_pos + BLOCK_SIZE
    
    def play(self):
        """Start playback using blocking writes in a thread."""
        if not self.tracks:
            return False
        
        if self.is_playing:
            return True
        
        try:
            # Get unique devices
            device_tracks = self._get_tracks_by_device()
            
            # Create blocking output streams for each device
            for device_index in device_tracks.keys():
                try:
                    stream = sd.OutputStream(
                        samplerate=self.sample_rate,
                        channels=2,
                        device=device_index,
                        blocksize=1024,
                        latency='low'
                    )
                    stream.start()
                    self.streams[device_index] = stream
                except Exception as e:
                    print(f"Error creating stream for device {device_index}: {e}")
            
            # Start playback
            self._stop_event.clear()
            self.is_playing = True
            
            # Start playback thread
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()
            
            return True
        except Exception as e:
            print(f"Playback error: {e}")
            self.is_playing = False
            return False
    
    def pause(self):
        """Pause playback."""
        self._stop_event.set()
        self.is_playing = False
        
        # Wait for thread to finish
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=0.5)
        
        # Close streams
        for stream in self.streams.values():
            try:
                stream.stop()
                stream.close()
            except:
                pass
        self.streams.clear()
    
    def stop(self):
        """Stop and reset."""
        self.pause()
        with self.lock:
            self.position = self.loop_start if self.loop_enabled else 0
    
    def toggle_play(self):
        """Toggle play/pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()
        return self.is_playing
    
    def set_loop(self, enabled, start_samples=None, end_samples=None):
        """Set loop points."""
        with self.lock:
            self.loop_enabled = enabled
            if start_samples is not None:
                self.loop_start = int(start_samples)
            if end_samples is not None:
                self.loop_end = int(end_samples)
    
    def set_track_device(self, track_id, device_index):
        """Set output device for a specific track."""
        for track in self.tracks:
            if track.id == track_id:
                old_device = track.device
                track.device = device_index
                
                # Rebuild streams if device changed while playing
                if old_device != device_index and self.is_playing:
                    saved_position = self.position
                    self.pause()
                    self.position = saved_position
                    self.play()
                break
    
    def cleanup(self):
        """Clean up all resources."""
        self.stop()
        for track in self.tracks:
            track.cleanup()
            track.cleanup()


class CSLPData:
    """Container for CSLP file data."""
    
    def __init__(self):
        self.timeline = []  # List of {time, text, notation, id}
        self.metadata = {}
        self.directory = ""  # Directory of the CSLP file for resolving relative paths
        
    def load(self, filepath):
        """Load CSLP file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get('data', {}).get('metadata', {})
            self.timeline = data.get('data', {}).get('timeline', [])
            self.directory = str(Path(filepath).parent)  # Store directory for relative path resolution
            
            print(f"[DEBUG] CSLPData.load - Loaded metadata: {self.metadata}")
            print(f"[DEBUG] CSLPData.load - Loaded {len(self.timeline)} timeline entries")
            
            # Ensure timeline is sorted by time
            self.timeline.sort(key=lambda x: x.get('time', 0))
            
            return True, f"Loaded {len(self.timeline)} markers"
        except Exception as e:
            return False, str(e)
    
    def get_entry_at_time(self, seconds):
        """Get the timeline entry for a given time."""
        current_entry = {'text': '', 'notation': '', 'time': 0}
        
        for entry in reversed(self.timeline):
            if entry and 'time' in entry and seconds >= entry['time']:
                current_entry = {
                    'text': str(entry.get('text', '') or '').strip(),
                    'notation': str(entry.get('notation', '') or '').strip(),
                    'time': entry.get('time', 0)
                }
                break
        
        return current_entry
    
    def get_marker_times(self):
        """Get list of marker times in seconds."""
        return [entry.get('time', 0) for entry in self.timeline]


class LyricsDisplayWidget(QWidget):
    """Widget to display current lyrics and notation."""
    
    log_message = pyqtSignal(str)  # Signal to send log messages to main window
    
    def __init__(self):
        super().__init__()
        self.lyrics = ""
        self.notation = ""
        self.current_id = -1
        self.directory = ""  # Directory for resolving relative image paths
        self.current_line_index = -1  # Index of currently playing line
        self.display_lines = []  # List of lines being displayed
        self.setMinimumHeight(80)
        # Remove maximum height constraint to allow expansion
        # self.setMaximumHeight(120)
        
    def set_content(self, lyrics, notation):
        """Update displayed lyrics and notation."""
        self.lyrics = lyrics
        self.notation = notation
        self.update()
    
    def set_directory(self, directory):
        """Set the directory for resolving relative image paths."""
        self.directory = directory
    
    def load_image_from_src(self, img_url, painter, rect):
        """Load and draw image from src URL/path, with logging."""
        try:
            # Log the original src
            log_msg = f"Image tag detected: {img_url}"
            self.log_message.emit(log_msg)
            print(f"[IMAGE LOG] {log_msg}")  # Also print to console
            
            # Check if it's just a filename (no path separators) - load from LyricsImages folder
            if not ('/' in img_url or '\\' in img_url or img_url.startswith('http')) and self.directory:
                img_url = str(Path(self.directory) / "LyricsImages" / img_url)
                log_msg = f"Resolved filename to LyricsImages folder: {img_url}"
                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
            
            # Try to load from URL or local file
            if img_url.startswith('http://') or img_url.startswith('https://'):
                log_msg = f"Loading image from URL: {img_url}"
                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
                try:
                    import ssl
                    from urllib.request import urlopen
                    from PyQt6.QtCore import QByteArray
                    
                    # Create SSL context to handle HTTPS properly
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    # Try to open the URL
                    log_msg = f"Opening URL connection..."
                    self.log_message.emit(log_msg)
                    print(f"[IMAGE LOG] {log_msg}")
                    with urlopen(img_url, context=ssl_context, timeout=10) as response:
                        log_msg = f"URL response status: {getattr(response, 'status', 'unknown')}"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                        data = response.read()
                        log_msg = f"Downloaded {len(data)} bytes of data"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                    
                    # Try to load the data into a pixmap
                    pixmap = QPixmap()
                    success = pixmap.loadFromData(data)
                    
                    if not success:
                        log_msg = f"Failed to parse image data from URL: {img_url} (data size: {len(data)} bytes)"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                        # Try to detect if it's HTML error page
                        try:
                            text_data = data.decode('utf-8', errors='ignore')
                            if '<html' in text_data.lower() or '<!doctype' in text_data.lower():
                                log_msg = "URL returned HTML instead of image data - likely a 404 or access error"
                                self.log_message.emit(log_msg)
                                print(f"[IMAGE LOG] {log_msg}")
                        except:
                            pass
                        return False
                    else:
                        log_msg = f"Successfully parsed image data from URL"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                        
                except Exception as url_error:
                    log_msg = f"Failed to download image from URL: {url_error}"
                    self.log_message.emit(log_msg)
                    print(f"[IMAGE LOG] {log_msg}")
                    log_msg = f"Error type: {type(url_error).__name__}"
                    self.log_message.emit(log_msg)
                    print(f"[IMAGE LOG] {log_msg}")
                    return False
            else:
                # Resolve relative paths using CSLP directory
                original_url = img_url
                if not Path(img_url).is_absolute() and self.directory:
                    img_url = str(Path(self.directory) / img_url)
                    log_msg = f"Resolved relative path: {original_url} → {img_url}"
                    self.log_message.emit(log_msg)
                    print(f"[IMAGE LOG] {log_msg}")
                else:
                    log_msg = f"Loading image from absolute path: {img_url}"
                    self.log_message.emit(log_msg)
                    print(f"[IMAGE LOG] {log_msg}")
                
                # Check if file exists
                if not Path(img_url).exists():
                    log_msg = f"Image file does not exist: {img_url}"
                    self.log_message.emit(log_msg)
                    print(f"[IMAGE LOG] {log_msg}")
                    return False
                
                log_msg = f"Attempting to load image file: {img_url}"
                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
                pixmap = QPixmap(img_url)
                log_msg = f"QPixmap created, isNull: {pixmap.isNull()}"
                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
                
                if pixmap.isNull():
                    # Try to get more info about why it failed
                    try:
                        import os
                        file_size = os.path.getsize(img_url)
                        log_msg = f"File exists, size: {file_size} bytes"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                    except Exception as size_error:
                        log_msg = f"Could not get file size: {size_error}"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                    
                    # Try alternative loading method
                    try:
                        with open(img_url, 'rb') as f:
                            data = f.read()
                        log_msg = f"Read {len(data)} bytes from file"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                        pixmap = QPixmap()
                        success = pixmap.loadFromData(data)
                        log_msg = f"loadFromData result: {success}"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
                        if success:
                            log_msg = "Alternative loading method succeeded!"
                            self.log_message.emit(log_msg)
                            print(f"[IMAGE LOG] {log_msg}")
                        else:
                            log_msg = "Alternative loading method also failed"
                            self.log_message.emit(log_msg)
                            print(f"[IMAGE LOG] {log_msg}")
                    except Exception as alt_error:
                        log_msg = f"Alternative loading failed: {alt_error}"
                        self.log_message.emit(log_msg)
                        print(f"[IMAGE LOG] {log_msg}")
            
            if not pixmap.isNull():
                log_msg = f"Image loaded successfully: {pixmap.width()}x{pixmap.height()}"
                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
                # Scale image appropriately for the notation area
                available_w = rect.width()
                available_h = rect.height()
                img_w = pixmap.width()
                img_h = pixmap.height()

                if img_w <= available_w and img_h <= available_h:
                    # Image is smaller than available space - center it without scaling
                    scaled = pixmap
                    x = rect.x() + (available_w - img_w) // 2
                    y = rect.y() + (available_h - img_h) // 2
                    log_msg = f"Image smaller than area, centering without scaling: {img_w}x{img_h} in {available_w}x{available_h}"
                else:
                    # Image is larger - scale down to fit while maintaining aspect ratio
                    scale_w = available_w / img_w
                    scale_h = available_h / img_h
                    scale = min(scale_w, scale_h)

                    new_w = int(img_w * scale)
                    new_h = int(img_h * scale)

                    scaled = pixmap.scaled(new_w, new_h, aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio, transformMode=Qt.TransformationMode.SmoothTransformation)
                    x = rect.x() + (available_w - new_w) // 2
                    y = rect.y() + (available_h - new_h) // 2
                    log_msg = f"Image larger than area, scaled to fit: {new_w}x{new_h} (scale: {scale:.2f})"

                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
                painter.drawPixmap(x, y, scaled)
                return True
            else:
                log_msg = f"Failed to load image: pixmap is null (unsupported format or corrupted file)"
                self.log_message.emit(log_msg)
                print(f"[IMAGE LOG] {log_msg}")
                return False
        except Exception as e:
            log_msg = f"Image loading error: {e}"
            self.log_message.emit(log_msg)
            print(f"[IMAGE LOG] {log_msg}")
            return False
    
    def update_display(self, current_time, timeline):
        """Update display based on current playback time."""
        # Find the current entry and collect upcoming entries to show at least 4 lines
        current_entry = {'text': '', 'notation': '', 'time': -1}
        current_index = -1
        
        # Find current entry
        for i, entry in enumerate(reversed(timeline)):
            if entry and 'time' in entry and current_time >= entry['time']:
                current_entry = {
                    'text': str(entry.get('text', '') or '').strip(),
                    'notation': str(entry.get('notation', '') or '').strip(),
                    'time': entry.get('time', 0)
                }
                current_index = len(timeline) - 1 - i
                break
        
        # Collect entries to display (current + upcoming to reach at least 4 lines)
        display_entries = []
        
        # Start from current entry
        start_index = max(0, current_index)
        
        # Collect up to 4 entries starting from current
        for i in range(start_index, min(start_index + 4, len(timeline))):
            entry = timeline[i]
            if entry:
                display_entries.append({
                    'text': str(entry.get('text', '') or '').strip(),
                    'notation': str(entry.get('notation', '') or '').strip(),
                    'time': entry.get('time', 0),
                    'is_current': (i == current_index)
                })
        
        # Store display lines for highlighting - each entry becomes one or two lines
        self.display_lines = []
        for entry in display_entries:
            if entry['text']:
                self.display_lines.append({'type': 'text', 'content': entry['text'], 'is_current': entry['is_current']})
            if entry['notation']:
                self.display_lines.append({'type': 'notation', 'content': entry['notation'], 'is_current': entry['is_current']})
        
        # Set current line index to the first current line
        self.current_line_index = -1
        for i, line in enumerate(self.display_lines):
            if line['is_current']:
                self.current_line_index = i
                break
        
        # Combine all entries into display text (lyrics and notation together)
        combined_text = ""
        
        for j, entry in enumerate(display_entries):
            # Calculate the timeline index for this entry
            timeline_index = start_index + j
            
            # Add lyrics if present
            if entry['text']:
                if combined_text:
                    combined_text += "\n"
                combined_text += f"{timeline_index + 1}. {entry['text']}"
            
            # Add notation if present (without serial number)
            if entry['notation']:
                if combined_text:
                    combined_text += "\n"
                combined_text += entry['notation']
        
        # Only update if changed
        if current_entry['time'] != self.current_id:
            self.current_id = current_entry['time']
            self.set_content(combined_text, "")  # Put everything in lyrics, leave notation empty
    
    def paintEvent(self, event):
        """Draw lyrics and notation, supporting <img src=...> in both."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(25, 25, 30))
        w = self.width()
        h = self.height()

        # Draw combined lyrics and notation (full area)
        full_rect = QRect(0, 0, w, h)
        if self.lyrics:
            import re
            img_match = re.search(r'<img\s+src\s*=\s*["\']([^"\']+)["\']', self.lyrics, re.IGNORECASE)
            print(f"[REGEX LOG] Checking lyrics: {repr(self.lyrics[:100])}")
            if img_match:
                print(f"[REGEX LOG] Found img tag in lyrics: {img_match.group(1)}")
                img_url = img_match.group(1)
                if not self.load_image_from_src(img_url, painter, full_rect):
                    # Fallback: draw error text
                    font = QFont("Segoe UI", 12, QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.setPen(QColor(255, 100, 100))
                    painter.drawText(full_rect, Qt.AlignmentFlag.AlignCenter, f"[Image error: {img_url}]")
            else:
                print(f"[REGEX LOG] No img tag found in lyrics")
                # Split lyrics into lines for highlighting
                lines = self.lyrics.split('\n')
                font = QFont("Segoe UI", 12, QFont.Weight.Normal)
                painter.setFont(font)
                
                # Calculate line height
                font_metrics = painter.fontMetrics()
                line_height = font_metrics.height()
                
                # Draw each line with highlighting if it's the current line
                y_offset = 10  # Start from top with some padding
                
                for i, line in enumerate(lines):
                    # Check if this line corresponds to the current playing line
                    is_current_line = (self.current_line_index >= 0 and 
                                     i < len(self.display_lines) and 
                                     self.display_lines[i].get('is_current', False))
                    
                    if is_current_line:
                        # Highlight current line with background
                        highlight_rect = QRect(0, y_offset - 2, w, line_height + 4)
                        painter.fillRect(highlight_rect, QColor(70, 100, 150, 180))  # Semi-transparent blue highlight
                        painter.setPen(QColor(255, 255, 200))  # Light yellow text for current line
                    else:
                        painter.setPen(QColor(200, 200, 200))  # Gray text for other lines
                    
                    # Draw the line (serial numbers are already included in combined_text)
                    display_line = line
                    
                    # Draw the line
                    text_width = font_metrics.horizontalAdvance(display_line)
                    x = max(10, (w - text_width) // 2)  # Center horizontally, but not less than 10
                    painter.drawText(x, y_offset + font_metrics.ascent(), display_line)
                    y_offset += line_height + 5  # Add some spacing between lines

        # Border
        painter.setPen(QPen(QColor(60, 60, 70)))
        painter.drawRect(0, 0, w - 1, h - 1)


class MarkersWidget(QWidget):
    """Widget to display clickable markers below waveform."""
    
    marker_clicked = pyqtSignal(float)  # Emits time in seconds
    
    def __init__(self):
        super().__init__()
        self.markers = []  # List of {time, label}
        self.duration = 0
        self.current_marker_index = -1
        self.setMinimumHeight(35)
        self.setMaximumHeight(35)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def set_markers(self, timeline, duration):
        """Set markers from CSLP timeline."""
        self.markers = []
        self.duration = duration
        
        for i, entry in enumerate(timeline):
            self.markers.append({
                'time': entry.get('time', 0),
                'label': str(i + 1),
                'text': entry.get('text', '')[:20]  # First 20 chars for tooltip
            })
        
        self.update()
    
    def set_current_time(self, seconds):
        """Update which marker is current."""
        new_index = -1
        for i, marker in enumerate(self.markers):
            if seconds >= marker['time']:
                new_index = i
        
        if new_index != self.current_marker_index:
            self.current_marker_index = new_index
            self.update()
    
    def paintEvent(self, event):
        """Draw markers."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(35, 35, 40))
        
        if not self.markers or self.duration <= 0:
            return
        
        w = self.width()
        h = self.height()
        
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        
        for i, marker in enumerate(self.markers):
            x = int((marker['time'] / self.duration) * w)
            
            # Marker line
            if i == self.current_marker_index:
                painter.setPen(QPen(QColor(100, 255, 100), 2))
                painter.setBrush(QBrush(QColor(100, 255, 100)))
            else:
                painter.setPen(QPen(QColor(100, 150, 200), 1))
                painter.setBrush(QBrush(QColor(70, 100, 140)))
            
            # Draw marker tick
            painter.drawLine(x, 0, x, 10)
            
            # Draw marker number
            painter.drawEllipse(x - 10, 12, 20, 18)
            painter.setPen(QColor(255, 255, 255) if i == self.current_marker_index else QColor(200, 200, 200))
            painter.drawText(x - 10, 12, 20, 18, Qt.AlignmentFlag.AlignCenter, marker['label'])
    
    def mousePressEvent(self, event):
        """Handle click to jump to marker."""
        if event.button() == Qt.MouseButton.LeftButton and self.duration > 0:
            x = event.position().x()
            w = self.width()
            
            # Find nearest marker
            click_time = (x / w) * self.duration
            nearest_marker = None
            min_dist = float('inf')
            
            for marker in self.markers:
                dist = abs(marker['time'] - click_time)
                # Check if click is within ~20 pixels of marker
                marker_x = (marker['time'] / self.duration) * w
                if abs(x - marker_x) < 20 and dist < min_dist:
                    min_dist = dist
                    nearest_marker = marker
            
            if nearest_marker:
                self.marker_clicked.emit(nearest_marker['time'])


class WaveformWidget(QWidget):
    """Widget to display audio waveform with playhead."""
    
    position_clicked = pyqtSignal(float)  # Emits position as ratio (0-1)
    loop_changed = pyqtSignal(float, float)  # Emits loop start and end ratios
    
    def __init__(self):
        super().__init__()
        self.waveform_data = None  # Downsampled waveform for display
        self.position_ratio = 0  # 0-1 position
        self.loop_start_ratio = 0
        self.loop_end_ratio = 1
        self.loop_enabled = False
        self.setMinimumHeight(100)
        self.setMouseTracking(True)
        
        # Dragging state
        self.dragging = None  # None, 'start', 'end', or 'seek'
        self.drag_threshold = 10  # pixels
        
        # Snap to markers
        self.marker_ratios = []  # List of marker positions as ratios (0-1)
        self.snap_enabled = False
        self.snap_threshold = 0.02  # 2% of track width for snapping
    
    def set_marker_ratios(self, ratios):
        """Set marker positions for snapping."""
        self.marker_ratios = sorted(ratios)
    
    def set_snap_enabled(self, enabled):
        """Enable/disable snap to markers."""
        self.snap_enabled = enabled
    
    def _snap_to_marker(self, ratio):
        """Snap ratio to nearest marker if within threshold."""
        if not self.snap_enabled or not self.marker_ratios:
            return ratio
        
        for marker_ratio in self.marker_ratios:
            if abs(ratio - marker_ratio) < self.snap_threshold:
                return marker_ratio
        return ratio
        
    def set_audio_data(self, audio_data, downsample_factor=500):
        """Set audio data and create waveform for display."""
        if audio_data is None:
            self.waveform_data = None
            self.update()
            return
        
        # Downsample for display (take max of each chunk)
        # Use mono mix for waveform
        if len(audio_data.shape) > 1:
            mono = np.mean(audio_data, axis=1)
        else:
            mono = audio_data
        
        # Downsample by taking max of chunks
        chunk_size = max(1, len(mono) // 1000)
        chunks = len(mono) // chunk_size
        reshaped = mono[:chunks * chunk_size].reshape(chunks, chunk_size)
        
        self.waveform_data = np.max(np.abs(reshaped), axis=1)
        self.update()
    
    def set_position(self, ratio):
        """Set playhead position (0-1)."""
        self.position_ratio = max(0, min(1, ratio))
        self.update()
    
    def set_loop(self, enabled, start_ratio=0, end_ratio=1):
        """Set loop display."""
        self.loop_enabled = enabled
        self.loop_start_ratio = start_ratio
        self.loop_end_ratio = end_ratio
        self.update()
    
    def paintEvent(self, event):
        """Draw the waveform."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 35))
        
        w = self.width()
        h = self.height()
        center_y = h // 2
        
        # Draw loop region
        if self.loop_enabled:
            loop_x1 = int(self.loop_start_ratio * w)
            loop_x2 = int(self.loop_end_ratio * w)
            painter.fillRect(loop_x1, 0, loop_x2 - loop_x1, h, QColor(50, 80, 50, 40))
        
        # Draw waveform
        if self.waveform_data is not None and len(self.waveform_data) > 0:
            pen = QPen(QColor(100, 180, 255))
            pen.setWidth(1)
            painter.setPen(pen)
            
            points_per_pixel = len(self.waveform_data) / w
            
            for x in range(w):
                idx = int(x * points_per_pixel)
                if idx < len(self.waveform_data):
                    amplitude = self.waveform_data[idx]
                    bar_height = int(amplitude * center_y * 0.9)
                    painter.drawLine(x, center_y - bar_height, x, center_y + bar_height)
        
        # Draw center line
        painter.setPen(QPen(QColor(80, 80, 80)))
        painter.drawLine(0, center_y, w, center_y)
        
        # Draw playhead
        playhead_x = int(self.position_ratio * w)
        pen = QPen(QColor(255, 100, 100))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(playhead_x, 0, playhead_x, h)
        
        # Draw loop markers
        if self.loop_enabled:
            pen = QPen(QColor(100, 255, 100))
            pen.setWidth(3)
            painter.setPen(pen)
            loop_x1 = int(self.loop_start_ratio * w)
            loop_x2 = int(self.loop_end_ratio * w)
            painter.drawLine(loop_x1, 0, loop_x1, h)
            painter.drawLine(loop_x2, 0, loop_x2, h)
            
            # Draw handles for loop markers
            handle_size = 8
            painter.setBrush(QBrush(QColor(100, 255, 100)))
            painter.drawRect(loop_x1 - handle_size//2, 0, handle_size, 15)
            painter.drawRect(loop_x1 - handle_size//2, h - 15, handle_size, 15)
            painter.drawRect(loop_x2 - handle_size//2, 0, handle_size, 15)
            painter.drawRect(loop_x2 - handle_size//2, h - 15, handle_size, 15)
    
    def _get_drag_target(self, x):
        """Determine what the mouse is over."""
        if not self.loop_enabled:
            return 'seek'
        
        w = self.width()
        loop_x1 = int(self.loop_start_ratio * w)
        loop_x2 = int(self.loop_end_ratio * w)
        
        if abs(x - loop_x1) < self.drag_threshold:
            return 'start'
        elif abs(x - loop_x2) < self.drag_threshold:
            return 'end'
        else:
            return 'seek'
    
    def mousePressEvent(self, event):
        """Handle click to seek or start dragging loop markers."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            self.dragging = self._get_drag_target(x)
            
            if self.dragging == 'seek':
                ratio = x / self.width()
                self.position_clicked.emit(ratio)
    
    def mouseMoveEvent(self, event):
        """Handle dragging loop markers."""
        x = event.position().x()
        w = self.width()
        ratio = max(0, min(1, x / w))
        
        # Update cursor
        target = self._get_drag_target(x)
        if target in ['start', 'end']:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Handle dragging
        if self.dragging == 'start':
            # Snap to marker if enabled
            snapped_ratio = self._snap_to_marker(ratio)
            # Don't let start go past end
            self.loop_start_ratio = min(snapped_ratio, self.loop_end_ratio - 0.01)
            self.update()
            self.loop_changed.emit(self.loop_start_ratio, self.loop_end_ratio)
        elif self.dragging == 'end':
            # Snap to marker if enabled
            snapped_ratio = self._snap_to_marker(ratio)
            # Don't let end go before start
            self.loop_end_ratio = max(snapped_ratio, self.loop_start_ratio + 0.01)
            self.update()
            self.loop_changed.emit(self.loop_start_ratio, self.loop_end_ratio)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.dragging = None


class MiniWaveformWidget(QWidget):
    """Smaller waveform for track display (no interaction)."""
    
    def __init__(self):
        super().__init__()
        self.waveform_data = None
        self.position_ratio = 0
        self.loop_enabled = False
        self.loop_start_ratio = 0
        self.loop_end_ratio = 1
        self.setMinimumHeight(60)
    
    def set_audio_data(self, audio_data):
        """Set audio data and create waveform."""
        if audio_data is None:
            self.waveform_data = None
            self.update()
            return
        
        if len(audio_data.shape) > 1:
            mono = np.mean(audio_data, axis=1)
        else:
            mono = audio_data
        
        chunk_size = max(1, len(mono) // 500)
        chunks = len(mono) // chunk_size
        reshaped = mono[:chunks * chunk_size].reshape(chunks, chunk_size)
        self.waveform_data = np.max(np.abs(reshaped), axis=1)
        self.update()
    
    def set_position(self, ratio):
        self.position_ratio = max(0, min(1, ratio))
        self.update()
    
    def set_loop(self, enabled, start_ratio=0, end_ratio=1):
        self.loop_enabled = enabled
        self.loop_start_ratio = start_ratio
        self.loop_end_ratio = end_ratio
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(35, 35, 40))
        
        w = self.width()
        h = self.height()
        center_y = h // 2
        
        # Loop region
        if self.loop_enabled:
            x1 = int(self.loop_start_ratio * w)
            x2 = int(self.loop_end_ratio * w)
            painter.fillRect(x1, 0, x2 - x1, h, QColor(50, 70, 50))
        
        # Waveform
        if self.waveform_data is not None and len(self.waveform_data) > 0:
            painter.setPen(QPen(QColor(80, 140, 200)))
            points_per_pixel = len(self.waveform_data) / w
            for x in range(w):
                idx = int(x * points_per_pixel)
                if idx < len(self.waveform_data):
                    amp = self.waveform_data[idx]
                    bar_h = int(amp * center_y * 0.8)
                    painter.drawLine(x, center_y - bar_h, x, center_y + bar_h)
        
        # Playhead
        if self.position_ratio > 0:
            x = int(self.position_ratio * w)
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawLine(x, 0, x, h)


class TrackWidget(QFrame):
    """Widget for a single track with controls and output device selector."""
    
    track_removed = pyqtSignal(int)  # Emits track ID
    track_changed = pyqtSignal(int)  # Emits track ID when settings change
    device_changed = pyqtSignal(int, object)  # Emits (track_id, device_index)
    
    def __init__(self, track, devices):
        super().__init__()
        self.track = track
        self.devices = devices  # List of (name, index) tuples
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Left side: controls
        controls = QVBoxLayout()
        controls.setSpacing(8)
        
        # Track name
        display_name = self._simplify_track_name(self.track.name)
        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 14px;")
        self.name_label.setMaximumWidth(200)
        self.name_label.setWordWrap(True)  # Enable word wrapping for long track names
        controls.addWidget(self.name_label)
        
        # Output device selector
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Out:"))
        self.device_combo = QComboBox()
        self.device_combo.setMaximumWidth(160)
        self.device_combo.setToolTip("Output device for this track")
        self.device_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                min-height: 24px;
            }
        """)
        # Populate devices
        for name, idx in self.devices:
            self.device_combo.addItem(name, idx)
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        device_layout.addWidget(self.device_combo, 1)
        controls.addLayout(device_layout)
        
        # Mute/Solo buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.mute_btn = QPushButton("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(32, 32)
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.setStyleSheet("""
            QPushButton { 
                background-color: #000000; 
                color: white;
                border: 1px solid #666666;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:checked { 
                background-color: #cc4444; 
                color: white; 
                border: 1px solid #ff6666;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.mute_btn.clicked.connect(self.on_mute_toggle)
        btn_layout.addWidget(self.mute_btn)
        
        self.solo_btn = QPushButton("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.setFixedSize(32, 32)
        self.solo_btn.setToolTip("Solo")
        self.solo_btn.setStyleSheet("""
            QPushButton { 
                background-color: #555555; 
                color: white;
                border: 1px solid #666666;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:checked { 
                background-color: #44aa44; 
                color: white; 
                border: 1px solid #66cc66;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.solo_btn.clicked.connect(self.on_solo_toggle)
        btn_layout.addWidget(self.solo_btn)
        
        # Volume slider inline with M/S
        btn_layout.addWidget(QLabel("Vol"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.setMaximumWidth(80)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        btn_layout.addWidget(self.volume_slider)
        
        btn_layout.addStretch()
        controls.addLayout(btn_layout)
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls)
        controls_widget.setMinimumWidth(220)
        layout.addWidget(controls_widget)
        
        # Remove button
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(32, 32)
        self.remove_btn.setToolTip("Remove track")
        self.remove_btn.setStyleSheet("""
            QPushButton { 
                background-color: #553333; 
                color: #ffffff;
                border: 1px solid #664444;
                border-radius: 3px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #774444;
                color: #ffaaaa;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.track_removed.emit(self.track.id))
        layout.addWidget(self.remove_btn)
        
        self.setStyleSheet("""
            TrackWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
            }
        """)
        self.setMinimumHeight(110)
        self.setMaximumHeight(120)
    
    def on_device_changed(self, index):
        """Handle device selection change."""
        device_index = self.device_combo.currentData()
        self.track.device = device_index
        self.device_changed.emit(self.track.id, device_index)
    
    def on_mute_toggle(self):
        self.track.muted = self.mute_btn.isChecked()
        self.track_changed.emit(self.track.id)
    
    def on_solo_toggle(self):
        self.track.solo = self.solo_btn.isChecked()
        self.track_changed.emit(self.track.id)
    
    def on_volume_changed(self, value):
        self.track.volume = value / 100.0
        self.volume_slider.setToolTip(f"Volume: {value}%")
        self.track_changed.emit(self.track.id)
    
    def set_position(self, ratio):
        """Update waveform playhead position."""
        self.waveform.set_position(ratio)
    
    def set_loop(self, enabled, start_ratio, end_ratio):
        """Update loop markers on waveform."""
        self.waveform.set_loop(enabled, start_ratio, end_ratio)
    
    def _simplify_track_name(self, track_name):
        """Simplify track names based on keywords.
        
        - If track name contains 'click', display 'Click'
        - If track name contains 'vocals', display 'Vocal'
        - If track name contains 'minus', display 'Minus'
        - Otherwise return the original name
        """
        track_name_lower = track_name.lower()
        if 'click' in track_name_lower:
            return 'Click'
        elif 'vocals' in track_name_lower:
            return 'Vocal'
        elif 'minus' in track_name_lower:
            return 'Minus'
        else:
            return track_name


class PrecisionPlayer(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.engine = MultiTrackEngine()  # Use multi-track engine
        self.cslp_data = CSLPData()
        self.current_file = None
        self.current_cslp = None
        self.track_widgets = []  # List of TrackWidget
        self.available_devices = []  # List of (name, index) tuples
        
        # Initialize project manager
        self.project_manager = ProjectManager()
        
        self.populate_devices()  # Populate devices before UI setup
        self.init_ui()
        self.setup_shortcuts()
        self.setup_timer()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Precision Audio Player")
        self.setMinimumSize(800, 400)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f23;
                color: #e6e6e6;
            }
            QLabel {
                color: #e6e6e6;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 400;
            }
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3748, stop:1 #1a202c);
                color: #e6e6e6;
                border: 1px solid #4a5568;
                padding: 12px 24px;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a5568, stop:1 #2d3748);
                border-color: #63b3ed;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a202c, stop:1 #0f0f23);
                border-color: #3182ce;
            }
            QPushButton:disabled {
                background-color: #2d3748;
                color: #718096;
                border-color: #4a5568;
            }
            QComboBox {
                background-color: #1a202c;
                color: #e6e6e6;
                border: 1px solid #4a5568;
                padding: 8px 12px;
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                min-height: 16px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e6e6e6;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a202c;
                color: #e6e6e6;
                selection-background-color: #3182ce;
                border: 1px solid #4a5568;
                border-radius: 4px;
            }
            QGroupBox {
                color: #e6e6e6;
                border: 2px solid #4a5568;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #63b3ed;
                font-size: 16px;
                font-weight: 600;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1a202c;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a5568;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #63b3ed;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # Top bar - File controls
        top_bar = QHBoxLayout()
        
        self.load_btn = QPushButton("📂 Add Track")
        self.load_btn.clicked.connect(self.add_track)
        top_bar.addWidget(self.load_btn)
        
        self.load_cslp_btn = QPushButton("📄 CSLP")
        self.load_cslp_btn.clicked.connect(self.load_cslp_file)
        top_bar.addWidget(self.load_cslp_btn)
        
        self.projects_btn = QPushButton("📋 Projects")
        self.projects_btn.clicked.connect(self.show_projects_dialog)
        top_bar.addWidget(self.projects_btn)
        
        self.save_project_btn = QPushButton("💾 Save")
        self.save_project_btn.clicked.connect(self.save_current_project)
        top_bar.addWidget(self.save_project_btn)
        
        top_bar.addStretch()
        
        self.file_label = QLabel("No tracks loaded")
        self.file_label.setStyleSheet("color: #a0aec0; font-style: italic;")
        top_bar.addWidget(self.file_label, 1)
        
        layout.addLayout(top_bar)
        
        # Lyrics/Notation display with border and title
        lyrics_group = QGroupBox("Lyrics / Notation")
        lyrics_layout = QVBoxLayout(lyrics_group)
        lyrics_layout.setContentsMargins(10, 20, 10, 10)
        self.lyrics_display = LyricsDisplayWidget()
        lyrics_layout.addWidget(self.lyrics_display)
        layout.addWidget(lyrics_group)
        
        # Tracks scroll area
        tracks_group = QGroupBox("Tracks")
        tracks_layout = QVBoxLayout(tracks_group)
        tracks_layout.setContentsMargins(10, 20, 10, 10)
        
        self.tracks_scroll = QScrollArea()
        self.tracks_scroll.setWidgetResizable(True)
        self.tracks_scroll.setMinimumHeight(120)
        self.tracks_scroll.setMaximumHeight(280)
        self.tracks_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.tracks_container = QWidget()
        self.tracks_container_layout = QHBoxLayout(self.tracks_container)
        self.tracks_container_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_container_layout.setSpacing(10)
        self.tracks_container_layout.addStretch()
        
        self.tracks_scroll.setWidget(self.tracks_container)
        tracks_layout.addWidget(self.tracks_scroll)
        
        # Container for waveform and markers
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        
        # Main waveform display (first track)
        self.waveform = WaveformWidget()
        self.waveform.position_clicked.connect(self.on_waveform_click)
        self.waveform.loop_changed.connect(self.on_loop_changed)
        bottom_layout.addWidget(self.waveform)
        
        # Markers display
        self.markers_widget = MarkersWidget()
        self.markers_widget.marker_clicked.connect(self.on_marker_clicked)
        bottom_layout.addWidget(self.markers_widget)
        
        # Waveform area with border and title
        waveform_group = QGroupBox("Waveform")
        waveform_layout = QVBoxLayout(waveform_group)
        waveform_layout.setContentsMargins(5, 15, 5, 5)
        waveform_layout.addWidget(bottom_container)
        
        # Create top-level splitter for all resizable sections
        top_splitter = QSplitter(Qt.Orientation.Vertical)
        top_splitter.addWidget(lyrics_group)
        top_splitter.addWidget(waveform_group)
        top_splitter.addWidget(tracks_group)
        
        top_splitter.setSizes([150, 200, 200])  # Initial sizes for lyrics, waveform, tracks
        
        layout.addWidget(top_splitter, 1)
        
        # Time display
        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00.00 / 00:00.00")
        self.time_label.setStyleSheet("""
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 16px;
            font-weight: 600;
            color: #63b3ed;
            background-color: transparent;
            padding: 8px 12px;
            border-radius: 4px;
        """)
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        
        self.loop_btn = QPushButton("🔁 Loop")
        self.loop_btn.setCheckable(True)
        self.loop_btn.clicked.connect(self.on_loop_toggle)
        time_layout.addWidget(self.loop_btn)
        
        self.snap_checkbox = QCheckBox("Snap")
        self.snap_checkbox.setToolTip("Snap loop markers to CSLP markers")
        self.snap_checkbox.stateChanged.connect(self.on_snap_changed)
        time_layout.addWidget(self.snap_checkbox)
        
        layout.addLayout(time_layout)
        
        # Transport controls
        transport = QHBoxLayout()
        transport.addStretch()
        
        # Metronome controls
        metronome_layout = QVBoxLayout()
        metronome_layout.setSpacing(2)
        
        metronome_controls = QHBoxLayout()
        metronome_controls.setSpacing(5)
        
        metronome_controls.addWidget(QLabel("BPM:"))
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(60, 200)
        self.bpm_spinbox.setValue(120)
        self.bpm_spinbox.setFixedWidth(60)
        metronome_controls.addWidget(self.bpm_spinbox)
        
        metronome_controls.addWidget(QLabel("Beats:"))
        self.beats_spinbox = QSpinBox()
        self.beats_spinbox.setRange(1, 8)
        self.beats_spinbox.setValue(4)
        self.beats_spinbox.setFixedWidth(50)
        metronome_controls.addWidget(self.beats_spinbox)
        
        metronome_layout.addLayout(metronome_controls)
        
        self.beat_counter_label = QLabel("Ready")
        self.beat_counter_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #888888;")
        self.beat_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        metronome_layout.addWidget(self.beat_counter_label)
        
        transport.addLayout(metronome_layout)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setEnabled(False)
        transport.addWidget(self.stop_btn)
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.on_play_pause)
        self.play_btn.setEnabled(False)
        self.play_btn.setMinimumWidth(120)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                font-size: 16px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
            }
        """)
        transport.addWidget(self.play_btn)
        
        self.play_with_countin_btn = QPushButton("▶ Count-in Play")
        self.play_with_countin_btn.clicked.connect(self.on_play_with_countin)
        self.play_with_countin_btn.setEnabled(False)
        self.play_with_countin_btn.setMinimumWidth(140)
        self.play_with_countin_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                font-size: 14px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
            }
        """)
        transport.addWidget(self.play_with_countin_btn)
        
        transport.addStretch()
        layout.addLayout(transport)
        
        # Status bar
        self.status_label = QLabel("Ready. Load an audio file to begin.")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Connect lyrics display logging
        self.lyrics_display.log_message.connect(self.status_label.setText)
    
    def populate_devices(self):
        """Populate available devices list for track widgets."""
        self.available_devices = []  # Store for track widgets
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        
        default_output = sd.default.device[1]
        
        # Track seen device names to avoid duplicates
        seen_devices = set()
        
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                # Get host API name
                hostapi_name = hostapis[dev['hostapi']]['name']
                
                # Create unique key to detect duplicates
                device_key = dev['name'].strip()
                
                # Skip if we've seen this device (keep first occurrence)
                if device_key in seen_devices:
                    continue
                seen_devices.add(device_key)
                
                # Prefer WASAPI or ASIO, show host API
                name = f"{dev['name']} [{hostapi_name}]"
                self.available_devices.append((name, i))
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.on_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.on_stop)
        QShortcut(QKeySequence("Ctrl+O"), self, self.add_track)
        QShortcut(QKeySequence(Qt.Key.Key_L), self, lambda: self.loop_btn.click())
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_current_project)
    
    def setup_timer(self):
        """Setup timer for UI updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(30)  # ~33fps update
        
        # Connect engine signals
        self.engine.position_changed.connect(self.on_position_changed)
    
    def add_track(self):
        """Add a new track from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Add Audio Track",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;All Files (*.*)"
        )
        
        if filepath:
            self.status_label.setText(f"Loading: {filepath}")
            QApplication.processEvents()
            
            # Add track to engine
            track = self.engine.add_track(filepath)
            
            if track.audio_data is not None:
                # Create track widget
                track_widget = TrackWidget(track, self.available_devices)
                track_widget.track_removed.connect(self.remove_track)
                track_widget.track_changed.connect(self.on_track_changed)
                track_widget.device_changed.connect(self.on_track_device_changed)
                
                # Insert before the stretch
                self.tracks_container_layout.insertWidget(
                    self.tracks_container_layout.count() - 1, track_widget
                )
                self.track_widgets.append(track_widget)
                
                # Update main waveform with first track
                if len(self.engine.tracks) == 1:
                    self.waveform.set_audio_data(track.audio_data)
                    self.current_file = Path(filepath)
                    
                    # Auto-load CSLP if exists
                    cslp_path = self.current_file.with_suffix('.cslp')
                    if cslp_path.exists():
                        self.load_cslp_from_path(str(cslp_path))
                
                self.play_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                self.play_with_countin_btn.setEnabled(True)
                self.file_label.setText(f"{len(self.engine.tracks)} track(s)")
                self.status_label.setText(f"Added: {track.name}")
            else:
                self.status_label.setText(f"Error loading track")
    
    def remove_track(self, track_id):
        """Remove a track by ID."""
        # Remove widget
        for widget in self.track_widgets:
            if widget.track.id == track_id:
                self.tracks_container_layout.removeWidget(widget)
                widget.deleteLater()
                self.track_widgets.remove(widget)
                break
        
        # Remove from engine
        self.engine.remove_track(track_id)
        
        # Update UI
        if not self.engine.tracks:
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.play_with_countin_btn.setEnabled(False)
            self.waveform.set_audio_data(None)
            self.file_label.setText("No tracks loaded")
        else:
            self.file_label.setText(f"{len(self.engine.tracks)} track(s)")
            # Update waveform with first remaining track
            self.waveform.set_audio_data(self.engine.tracks[0].audio_data)
        
        self.status_label.setText(f"Removed track {track_id}")
    
    def on_track_changed(self, track_id):
        """Handle track settings changed (mute/solo/volume)."""
        # Settings already applied to track object
        # Auto-save track settings if enabled
        if self.project_manager.current_project and self.project_manager.auto_save_enabled:
            track_settings = {}
            for widget in self.track_widgets:
                if widget.track and widget.track.filepath:
                    track_settings[str(widget.track.filepath)] = {
                        "volume": widget.track.volume,
                        "muted": widget.track.muted,
                        "solo": widget.track.solo,
                        "device": widget.track.device,
                        "name": widget.track.name
                    }
            self.project_manager.update_project_track_settings(track_settings)
    
    def on_track_device_changed(self, track_id, device_index):
        """Handle per-track device selection change."""
        self.engine.set_track_device(track_id, device_index)
        # Find the track name for status
        for widget in self.track_widgets:
            if widget.track.id == track_id:
                device_name = widget.device_combo.currentText()
                self.status_label.setText(f"{widget.track.name} → {device_name}")
                break
        
        # Auto-save track settings if enabled
        if self.project_manager.current_project and self.project_manager.auto_save_enabled:
            track_settings = {}
            for widget in self.track_widgets:
                if widget.track and widget.track.filepath:
                    track_settings[str(widget.track.filepath)] = {
                        "volume": widget.track.volume,
                        "muted": widget.track.muted,
                        "solo": widget.track.solo,
                        "device": widget.track.device,
                        "name": widget.track.name
                    }
            self.project_manager.update_project_track_settings(track_settings)
    
    def load_file(self):
        """Alias for add_track for compatibility."""
        self.add_track()
    
    def load_cslp_file(self):
        """Open file dialog and load CSLP markers."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open CSLP File",
            "",
            "CSLP Files (*.cslp);;JSON Files (*.json);;All Files (*.*)"
        )
        
        if filepath:
            self.load_cslp_from_path(filepath)
    
    def load_cslp_from_path(self, filepath):
        """Load CSLP file from path."""
        self.cslp_data = CSLPData()
        success, message = self.cslp_data.load(filepath)
        
        if success:
            # Set current CSLP file path regardless of whether there are markers
            self.current_cslp = Path(filepath)
            
            if self.cslp_data.timeline:
                # Set directory for image path resolution
                self.lyrics_display.set_directory(self.cslp_data.directory)
                
                # Pass markers to markers widget
                duration = self.engine.get_duration()
                self.markers_widget.set_markers(
                    self.cslp_data.timeline,
                    duration
                )
                
                # Set marker ratios for waveform snapping
                if duration > 0:
                    marker_ratios = [entry.get('time', 0) / duration for entry in self.cslp_data.timeline]
                    self.waveform.set_marker_ratios(marker_ratios)
                
                self.status_label.setText(
                    f"Loaded CSLP: {len(self.cslp_data.timeline)} markers"
                )
            else:
                self.status_label.setText("CSLP file loaded but has no markers")
        else:
            self.status_label.setText(f"Failed to load CSLP file: {message}")
    
    def on_snap_changed(self, state):
        """Handle snap checkbox toggle."""
        self.waveform.set_snap_enabled(state == Qt.CheckState.Checked.value)
    
    def on_marker_clicked(self, time_seconds):
        """Handle click on a marker - jump to that position."""
        if self.engine.tracks:
            sample_position = int(time_seconds * self.engine.sample_rate)
            self.engine.set_position_samples(sample_position)
            self.status_label.setText(
                f"Jumped to marker at {int(time_seconds//60):02d}:{time_seconds%60:05.2f}"
            )
    
    def on_position_changed(self, value):
        """Handle position changes from engine (used for beat counter during count-in)."""
        # During count-in, value is the current beat number
        if hasattr(self.engine, 'countin_current_beat') and self.engine.countin_current_beat <= self.engine.countin_beats:
            if value > 0:
                self.beat_counter_label.setText(str(value))
                # Flash the label
                self.beat_counter_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffff00;")
                QTimer.singleShot(200, lambda: self.beat_counter_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #888888;"))
        else:
            # Normal playback, reset counter
            if self.beat_counter_label.text() != "Ready":
                self.beat_counter_label.setText("Ready")
    
    def on_play_pause(self):
        """Handle play/pause button."""
        if not self.engine.tracks:
            return
        
        is_playing = self.engine.toggle_play()
        self.play_btn.setText("⏸ Pause" if is_playing else "▶ Play")
    
    def on_stop(self):
        """Handle stop button."""
        self.engine.stop()
        self.play_btn.setText("▶ Play")
        self.beat_counter_label.setText("Ready")
    
    def on_play_with_countin(self):
        """Handle play with count-in button."""
        if not self.engine.tracks:
            return
        
        bpm = self.bpm_spinbox.value()
        beats = self.beats_spinbox.value()
        
        # Start count-in playback
        self.engine.play_with_countin(bpm, beats)
        self.play_btn.setText("⏸ Pause")
        self.beat_counter_label.setText("1")  # Will be updated by timer
    
    def on_loop_toggle(self):
        """Handle loop toggle."""
        enabled = self.loop_btn.isChecked()
        
        if enabled and self.engine.tracks:
            # Set loop to full track for now (use first track's length)
            total_samples = self.engine.get_total_samples()
            self.engine.set_loop(True, 0, total_samples)
            self.waveform.set_loop(True, 0, 1)
        else:
            self.engine.set_loop(False)
            self.waveform.set_loop(False)
    
    def on_waveform_click(self, ratio):
        """Handle click on waveform to seek."""
        if self.engine.tracks:
            total_samples = self.engine.get_total_samples()
            self.engine.set_position_samples(int(ratio * total_samples))
    
    def on_loop_changed(self, start_ratio, end_ratio):
        """Handle loop markers being dragged."""
        if self.engine.tracks:
            total_samples = self.engine.get_total_samples()
            start_samples = int(start_ratio * total_samples)
            end_samples = int(end_ratio * total_samples)
            self.engine.set_loop(True, start_samples, end_samples)
    
    def update_ui(self):
        """Update UI elements (called by timer)."""
        if self.engine.tracks:
            # Update time display
            current = self.engine.get_position_seconds()
            total = self.engine.get_duration()
            
            current_str = f"{int(current // 60):02d}:{current % 60:05.2f}"
            total_str = f"{int(total // 60):02d}:{total % 60:05.2f}"
            self.time_label.setText(f"{current_str} / {total_str}")
            
            # Update waveform playhead
            ratio = current / total if total > 0 else 0
            self.waveform.set_position(ratio)
            
            # Update lyrics display
            if self.cslp_data and self.cslp_data.timeline:
                self.lyrics_display.update_display(current, self.cslp_data.timeline)
            
            # Update marker highlight
            if self.cslp_data:
                self.markers_widget.set_current_time(current)
            
            # Check if playback finished
            if not self.engine.is_playing and self.play_btn.text() == "⏸ Pause":
                self.play_btn.setText("▶ Play")
                self.beat_counter_label.setText("Ready")
    
    def show_projects_dialog(self):
        """Show the projects management dialog."""
        dialog = ProjectDialog(self.project_manager, self)
        dialog.project_selected.connect(self.load_project)
        dialog.exec()
    
    def load_project(self, project_data):
        """Load a project from project data."""
        try:
            project_name = project_data["name"]
            audio_files = project_data.get("audio_files", [])
            cslp_file = project_data.get("cslp_file")
            
            print(f"[DEBUG] Loading project: {project_name}")
            print(f"[DEBUG] Current tracks before clearing: {len(self.engine.tracks)}")
            print(f"[DEBUG] Current CSLP timeline entries: {len(self.cslp_data.timeline) if self.cslp_data else 0}")
            
            # Stop playback before loading
            self.engine.stop()
            print("[DEBUG] Playback stopped")
            
            # Clear current tracks
            self.clear_all_tracks()
            print(f"[DEBUG] Tracks cleared, remaining tracks: {len(self.engine.tracks)}")
            
            # Clear current CSLP data
            self.cslp_data = CSLPData()
            self.current_cslp = None
            self.update_cslp_display()
            print("[DEBUG] CSLP data cleared")
            
            # Load audio files
            loaded_count = 0
            for audio_file in audio_files:
                if Path(audio_file).exists():
                    self.add_track_from_file(audio_file)
                    loaded_count += 1
                    print(f"[DEBUG] Loaded audio file: {audio_file}")
                    
                    # Update main waveform with first track
                    if loaded_count == 1:
                        # Get the first track that was just added
                        if self.engine.tracks:
                            first_track = self.engine.tracks[-1]  # Last added track
                            self.waveform.set_audio_data(first_track.audio_data)
                            print("[DEBUG] Waveform updated with first track")
                else:
                    print(f"Warning: Audio file not found: {audio_file}")
            
            print(f"[DEBUG] Total tracks after loading: {len(self.engine.tracks)}")
            
            # Load CSLP file
            if cslp_file and Path(cslp_file).exists():
                self.load_cslp_from_file(cslp_file)
                print(f"[DEBUG] Loaded CSLP file: {cslp_file}")
            elif cslp_file:
                print(f"Warning: CSLP file not found: {cslp_file}")
            
            # Apply track settings if available
            track_settings = project_data.get("track_settings", {})
            if track_settings:
                for widget in self.track_widgets:
                    if widget.track and widget.track.filepath:
                        filepath_str = str(widget.track.filepath)
                        if filepath_str in track_settings:
                            settings = track_settings[filepath_str]
                            widget.track.volume = settings.get("volume", 1.0)
                            widget.track.muted = settings.get("muted", False)
                            widget.track.solo = settings.get("solo", False)
                            widget.track.device = settings.get("device")
                            widget.track.name = settings.get("name", widget.track.name)
                            
                            # Update UI to reflect loaded settings
                            widget.volume_slider.setValue(int(widget.track.volume * 100))
                            widget.mute_btn.setChecked(widget.track.muted)
                            widget.solo_btn.setChecked(widget.track.solo)
                            if widget.track.device is not None:
                                # Find the device index in the combo box
                                for i in range(widget.device_combo.count()):
                                    if widget.device_combo.itemData(i) == widget.track.device:
                                        widget.device_combo.setCurrentIndex(i)
                                        break
                            
                            print(f"[DEBUG] Applied settings for track: {filepath_str}")
            
            print(f"[DEBUG] Final CSLP timeline entries: {len(self.cslp_data.timeline)}")
            
            # Enable playback controls if tracks were loaded
            if loaded_count > 0:
                self.play_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                self.play_with_countin_btn.setEnabled(True)
                
                # Reset position and loop points
                self.engine.set_position_samples(0)
                self.waveform.set_position(0)
                self.update_ui()
                print("[DEBUG] Playback controls enabled and position reset")
            
            # Set current project
            self.project_manager.current_project = project_data
            self.project_manager.enable_auto_save()
            
            # Update status
            self.status_label.setText(f"Loaded project '{project_name}': {loaded_count} audio files, CSLP: {cslp_file or 'None'}")
            
            # Build project display text with metadata if available
            display_text = f"Project: {project_name}"
            if self.cslp_data and self.cslp_data.metadata:
                metadata = self.cslp_data.metadata
                print(f"[DEBUG] CSLP metadata found: {metadata}")
                raga = metadata.get('ragam', '')
                thalam = metadata.get('talam', '')
                aro = metadata.get('aarohanam', '')
                ava = metadata.get('avarohanam', '')
                print(f"[DEBUG] Extracted - Raga: '{raga}', Thalam: '{thalam}', Aro: '{aro}', Ava: '{ava}'")
                if raga or thalam or aro or ava:
                    metadata_parts = []
                    if raga: metadata_parts.append(f"Raga: {raga}")
                    if thalam: metadata_parts.append(f"Thalam: {thalam}")
                    if aro: metadata_parts.append(f"Aro: {aro}")
                    if ava: metadata_parts.append(f"Ava: {ava}")
                    display_text += f" ({', '.join(metadata_parts)})"
                    print(f"[DEBUG] Display text with metadata: {display_text}")
                else:
                    print("[DEBUG] No metadata fields found to display")
            else:
                print("[DEBUG] No CSLP data or metadata available")
            
            self.file_label.setText(display_text)
            
            print(f"[DEBUG] Project '{project_name}' loaded successfully")
            
        except Exception as e:
            print(f"[DEBUG] Error loading project: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load project: {e}")
    
    def save_current_project(self):
        """Save the current project."""
        if not self.project_manager.current_project:
            # Create new project
            name, ok = QInputDialog.getText(self, "Save Project", "Enter project name:")
            if not ok or not name.strip():
                return
            
            name = name.strip()
            audio_files = []
            track_settings = {}
            for widget in self.track_widgets:
                if widget.track and widget.track.filepath:
                    audio_files.append(str(widget.track.filepath))
                    # Store track settings keyed by filepath
                    track_settings[str(widget.track.filepath)] = {
                        "volume": widget.track.volume,
                        "muted": widget.track.muted,
                        "solo": widget.track.solo,
                        "device": widget.track.device,
                        "name": widget.track.name
                    }
            
            cslp_file = str(self.current_cslp) if self.current_cslp else None
            
            project = self.project_manager.create_project(name, audio_files, cslp_file, track_settings)
            if self.project_manager.save_project(project):
                self.project_manager.enable_auto_save()
                QMessageBox.information(self, "Success", f"Project '{name}' saved!")
                
                # Load CSLP data if available to update metadata display
                if cslp_file:
                    self.load_cslp_from_file(cslp_file)
                
                self.update_file_label()
            else:
                QMessageBox.critical(self, "Error", "Failed to save project.")
        else:
            # Update existing project
            audio_files = []
            track_settings = {}
            for widget in self.track_widgets:
                if widget.track and widget.track.filepath:
                    audio_files.append(str(widget.track.filepath))
                    # Store track settings keyed by filepath
                    track_settings[str(widget.track.filepath)] = {
                        "volume": widget.track.volume,
                        "muted": widget.track.muted,
                        "solo": widget.track.solo,
                        "device": widget.track.device,
                        "name": widget.track.name
                    }
            
            cslp_file = str(self.current_cslp) if self.current_cslp else None
            
            self.project_manager.update_project_audio(audio_files)
            self.project_manager.update_project_cslp(cslp_file)
            self.project_manager.update_project_track_settings(track_settings)
            
            if self.project_manager.save_project(self.project_manager.current_project):
                QMessageBox.information(self, "Success", f"Project '{self.project_manager.current_project['name']}' updated!")
            else:
                QMessageBox.critical(self, "Error", "Failed to update project.")
    
    def add_track_from_file(self, file_path):
        """Add a track from file path (used by project loading)."""
        try:
            # Use the engine's add_track method which handles loading
            track = self.engine.add_track(file_path)
            
            if track.audio_data is not None:
                # Create track widget
                track_widget = TrackWidget(track, self.available_devices)
                track_widget.track_changed.connect(self.on_track_changed)
                track_widget.track_removed.connect(self.remove_track)
                
                self.track_widgets.append(track_widget)
                self.tracks_container_layout.addWidget(track_widget)
                
                self.update_file_label()
            else:
                print(f"Failed to load audio data from {file_path}")
            
        except Exception as e:
            print(f"Error loading track {file_path}: {e}")
    
    def load_cslp_from_file(self, file_path):
        """Load CSLP from file path (used by project loading)."""
        try:
            success, message = self.cslp_data.load(file_path)
            if success:
                self.current_cslp = Path(file_path)
                self.update_cslp_display()
                self.status_label.setText(f"Loaded CSLP: {Path(file_path).name}")
            else:
                print(f"Failed to load CSLP {file_path}: {message}")
                self.current_cslp = None
        except Exception as e:
            print(f"Error loading CSLP {file_path}: {e}")
            self.current_cslp = None
    
    def update_cslp_display(self):
        """Update the display with current CSLP data."""
        if self.cslp_data.timeline:
            # Set directory for image path resolution
            self.lyrics_display.set_directory(self.cslp_data.directory)
            
            # Pass markers to markers widget
            duration = self.engine.get_duration()
            self.markers_widget.set_markers(
                self.cslp_data.timeline,
                duration
            )
            
            # Set marker ratios for waveform snapping
            if duration > 0:
                marker_ratios = [entry.get('time', 0) / duration for entry in self.cslp_data.timeline]
                self.waveform.set_marker_ratios(marker_ratios)
    
    def clear_all_tracks(self):
        """Clear all current tracks."""
        # Remove from engine
        for track_widget in self.track_widgets:
            if track_widget.track:
                self.engine.remove_track(track_widget.track.id)
        
        # Remove widgets
        for track_widget in self.track_widgets:
            track_widget.setParent(None)
            track_widget.deleteLater()
        
        self.track_widgets.clear()
        self.update_file_label()
    
    def update_file_label(self):
        """Update the file label to show current status."""
        if self.project_manager.current_project:
            project_name = self.project_manager.current_project['name']
            display_text = f"Project: {project_name}"
            
            # Add metadata if available
            if self.cslp_data and self.cslp_data.metadata:
                metadata = self.cslp_data.metadata
                print(f"[DEBUG] update_file_label - CSLP metadata found: {metadata}")
                raga = metadata.get('ragam', '')
                thalam = metadata.get('talam', '')
                aro = metadata.get('aarohanam', '')
                ava = metadata.get('avarohanam', '')
                print(f"[DEBUG] update_file_label - Extracted - Raga: '{raga}', Thalam: '{thalam}', Aro: '{aro}', Ava: '{ava}'")
                if raga or thalam or aro or ava:
                    metadata_parts = []
                    if raga: metadata_parts.append(f"Raga: {raga}")
                    if thalam: metadata_parts.append(f"Thalam: {thalam}")
                    if aro: metadata_parts.append(f"Aro: {aro}")
                    if ava: metadata_parts.append(f"Ava: {ava}")
                    display_text += f" ({', '.join(metadata_parts)})"
                    print(f"[DEBUG] update_file_label - Display text with metadata: {display_text}")
                else:
                    print("[DEBUG] update_file_label - No metadata fields found to display")
            else:
                print("[DEBUG] update_file_label - No CSLP data or metadata available")
            
            self.file_label.setText(display_text)
        elif self.engine.tracks:
            self.file_label.setText(f"{len(self.engine.tracks)} track(s)")
        else:
            self.file_label.setText("No tracks loaded")
    
    def on_track_changed(self):
        """Handle track changes for auto-save."""
        if self.project_manager.auto_save_enabled and self.project_manager.current_project:
            # Update audio files in project
            audio_files = []
            for widget in self.track_widgets:
                if widget.track and widget.track.filepath:
                    audio_files.append(str(widget.track.filepath))
            
            self.project_manager.update_project_audio(audio_files)
    
    def closeEvent(self, event):
        """Clean up on close."""
        # Auto-save current project if enabled
        if self.project_manager.current_project and self.project_manager.auto_save_enabled:
            self.project_manager.close_project()
        
        self.engine.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Check for audio devices
    devices = sd.query_devices()
    output_devices = [d for d in devices if d['max_output_channels'] > 0]
    
    if not output_devices:
        print("Error: No audio output devices found!")
        sys.exit(1)
    
    window = PrecisionPlayer()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
