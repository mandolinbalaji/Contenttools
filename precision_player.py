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

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QSlider, QFrame,
    QSplitter, QGroupBox, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QKeySequence, QShortcut, QFont


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
    """Represents a single audio track with its own settings."""
    
    def __init__(self, track_id, name="Track"):
        self.id = track_id
        self.name = name
        self.audio_data = None
        self.sample_rate = 44100
        self.channels = 2
        self.volume = 1.0  # 0.0 to 1.0
        self.muted = False
        self.solo = False
        self.device = None  # None = default/master
        self.filepath = None
    
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
    
    def get_samples(self, start, count):
        """Get audio samples with volume applied."""
        if self.audio_data is None:
            return np.zeros((count, 2), dtype='float32')
        
        end = min(start + count, len(self.audio_data))
        if start >= len(self.audio_data):
            return np.zeros((count, 2), dtype='float32')
        
        samples = self.audio_data[start:end].copy()
        
        # Apply volume
        if not self.muted:
            samples *= self.volume
        else:
            samples *= 0
        
        # Pad if needed
        if len(samples) < count:
            padding = np.zeros((count - len(samples), samples.shape[1]), dtype='float32')
            samples = np.vstack((samples, padding))
        
        return samples


class MultiTrackEngine(QObject):
    """Engine that manages multiple synchronized tracks."""
    
    position_changed = pyqtSignal(int)
    playback_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.tracks = []  # List of Track objects
        self.sample_rate = 44100
        self.position = 0
        self.is_playing = False
        self.stream = None
        self.master_device = None
        
        # Loop
        self.loop_enabled = False
        self.loop_start = 0
        self.loop_end = 0
        
        self.lock = threading.Lock()
    
    def add_track(self, filepath=None):
        """Add a new track."""
        track_id = len(self.tracks) + 1
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
        self.tracks = [t for t in self.tracks if t.id != track_id]
    
    def get_duration(self):
        """Get max duration across all tracks."""
        if not self.tracks:
            return 0
        max_samples = max((len(t.audio_data) if t.audio_data is not None else 0) for t in self.tracks)
        return max_samples / self.sample_rate
    
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
    
    def _audio_callback(self, outdata, frames, time, status):
        """Mix all tracks and output."""
        with self.lock:
            if not self.tracks or not self.is_playing:
                outdata.fill(0)
                return
            
            # Handle looping
            if self.loop_enabled:
                if self.position >= self.loop_end or self.position < self.loop_start:
                    self.position = self.loop_start
            
            # Check for solo
            has_solo = self._has_solo()
            
            # Mix tracks
            mixed = np.zeros((frames, 2), dtype='float32')
            
            for track in self.tracks:
                if track.audio_data is None:
                    continue
                
                # Skip if muted, or if there's a solo and this track isn't it
                if track.muted:
                    continue
                if has_solo and not track.solo:
                    continue
                
                # Get samples from track
                samples = track.get_samples(self.position, frames)
                mixed += samples
            
            # Handle loop wrap
            samples_before_loop = self.loop_end - self.position if self.loop_enabled else frames
            
            if self.loop_enabled and samples_before_loop < frames:
                # We need to wrap
                self.position = self.loop_start
                outdata[:samples_before_loop] = mixed[:samples_before_loop]
                
                # Get remaining samples from loop start
                remaining = frames - samples_before_loop
                mixed2 = np.zeros((remaining, 2), dtype='float32')
                
                for track in self.tracks:
                    if track.audio_data is None or track.muted:
                        continue
                    if has_solo and not track.solo:
                        continue
                    samples = track.get_samples(self.position, remaining)
                    mixed2 += samples
                
                outdata[samples_before_loop:] = mixed2
                self.position = self.loop_start + remaining
            else:
                outdata[:] = np.clip(mixed, -1.0, 1.0)
                self.position += frames
                
                # Check end of all tracks
                max_len = max((len(t.audio_data) if t.audio_data is not None else 0) for t in self.tracks)
                if self.position >= max_len and not self.loop_enabled:
                    self.is_playing = False
    
    def play(self):
        """Start playback."""
        if not self.tracks:
            return False
        
        if self.is_playing:
            return True
        
        try:
            self.is_playing = True
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                callback=self._audio_callback,
                device=self.master_device,
                blocksize=512,
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
    
    def set_device(self, device_index):
        """Set master output device."""
        self.master_device = device_index
        if self.is_playing:
            self.pause()
            self.play()
    
    def cleanup(self):
        """Clean up."""
        self.stop()


class CSLPData:
    """Container for CSLP file data."""
    
    def __init__(self):
        self.timeline = []  # List of {time, text, notation, id}
        self.metadata = {}
        
    def load(self, filepath):
        """Load CSLP file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get('metadata', {})
            self.timeline = data.get('data', {}).get('timeline', [])
            
            # Ensure timeline is sorted by time
            self.timeline.sort(key=lambda x: x.get('time', 0))
            
            return True, f"Loaded {len(self.timeline)} markers"
        except Exception as e:
            return False, str(e)
    
    def get_entry_at_time(self, seconds):
        """Get the timeline entry for a given time."""
        current_entry = {'text': '', 'notation': '', 'id': 0}
        
        for entry in reversed(self.timeline):
            if entry and 'time' in entry and seconds >= entry['time']:
                current_entry = {
                    'text': str(entry.get('text', '') or '').strip(),
                    'notation': str(entry.get('notation', '') or '').strip(),
                    'id': entry.get('id', 0),
                    'time': entry.get('time', 0)
                }
                break
        
        return current_entry
    
    def get_marker_times(self):
        """Get list of marker times in seconds."""
        return [entry.get('time', 0) for entry in self.timeline]


class LyricsDisplayWidget(QWidget):
    """Widget to display current lyrics and notation."""
    
    def __init__(self):
        super().__init__()
        self.lyrics = ""
        self.notation = ""
        self.current_id = -1
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        
    def set_content(self, lyrics, notation):
        """Update displayed lyrics and notation."""
        self.lyrics = lyrics
        self.notation = notation
        self.update()
    
    def update_display(self, current_time, timeline):
        """Update display based on current playback time."""
        # Find the current entry
        current_entry = {'text': '', 'notation': '', 'id': -1}
        
        for entry in reversed(timeline):
            if entry and 'time' in entry and current_time >= entry['time']:
                current_entry = {
                    'text': str(entry.get('text', '') or '').strip(),
                    'notation': str(entry.get('notation', '') or '').strip(),
                    'id': entry.get('id', 0)
                }
                break
        
        # Only update if changed
        if current_entry['id'] != self.current_id:
            self.current_id = current_entry['id']
            self.set_content(current_entry['text'], current_entry['notation'])
    
    def paintEvent(self, event):
        """Draw lyrics and notation."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(25, 25, 30))
        
        w = self.width()
        h = self.height()
        
        # Draw lyrics (larger, top)
        if self.lyrics:
            font = QFont("Segoe UI", 18, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(0, 0, w, h // 2 + 10, 
                           Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                           self.lyrics)
        
        # Draw notation (smaller, bottom)
        if self.notation:
            font = QFont("Consolas", 14)
            painter.setFont(font)
            painter.setPen(QColor(180, 220, 255))
            painter.drawText(0, h // 2, w, h // 2, 
                           Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
                           self.notation)
        
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
            painter.fillRect(loop_x1, 0, loop_x2 - loop_x1, h, QColor(50, 80, 50))
        
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
    """Widget for a single track with controls."""
    
    track_removed = pyqtSignal(int)  # Emits track ID
    track_changed = pyqtSignal(int)  # Emits track ID when settings change
    
    def __init__(self, track, devices):
        super().__init__()
        self.track = track
        self.devices = devices
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Left side: controls
        controls = QVBoxLayout()
        controls.setSpacing(4)
        
        # Track name
        self.name_label = QLabel(self.track.name)
        self.name_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.name_label.setMaximumWidth(150)
        controls.addWidget(self.name_label)
        
        # Mute/Solo buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        self.mute_btn = QPushButton("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(28, 28)
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.setStyleSheet("""
            QPushButton { 
                background-color: #555555; 
                color: #cccccc;
                border: 1px solid #666666;
                border-radius: 3px;
                font-weight: bold;
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
        self.solo_btn.setFixedSize(28, 28)
        self.solo_btn.setToolTip("Solo")
        self.solo_btn.setStyleSheet("""
            QPushButton { 
                background-color: #555555; 
                color: #cccccc;
                border: 1px solid #666666;
                border-radius: 3px;
                font-weight: bold;
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
        
        btn_layout.addStretch()
        controls.addLayout(btn_layout)
        
        # Volume slider
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Vol"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setMaximumWidth(80)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        vol_layout.addWidget(self.volume_slider)
        controls.addLayout(vol_layout)
        
        controls.addStretch()
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls)
        controls_widget.setMaximumWidth(120)
        controls_widget.setMinimumWidth(120)
        layout.addWidget(controls_widget)
        
        # Mini waveform (right side, expandable)
        self.waveform = MiniWaveformWidget()
        if self.track.audio_data is not None:
            self.waveform.set_audio_data(self.track.audio_data)
        layout.addWidget(self.waveform, 1)
        
        # Remove button
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setToolTip("Remove track")
        self.remove_btn.setStyleSheet("""
            QPushButton { 
                background-color: #553333; 
                color: #ff8888;
                border: 1px solid #664444;
                border-radius: 3px;
                font-weight: bold;
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
                border-radius: 4px;
            }
        """)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)
    
    def on_mute_toggle(self):
        self.track.muted = self.mute_btn.isChecked()
        self.track_changed.emit(self.track.id)
    
    def on_solo_toggle(self):
        self.track.solo = self.solo_btn.isChecked()
        self.track_changed.emit(self.track.id)
    
    def on_volume_changed(self, value):
        self.track.volume = value / 100.0
        self.track_changed.emit(self.track.id)
    
    def set_position(self, ratio):
        """Update waveform playhead position."""
        self.waveform.set_position(ratio)
    
    def set_loop(self, enabled, start_ratio, end_ratio):
        """Update loop markers on waveform."""
        self.waveform.set_loop(enabled, start_ratio, end_ratio)


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
        
        self.init_ui()
        self.setup_shortcuts()
        self.setup_timer()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Precision Audio Player")
        self.setMinimumSize(800, 400)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Top bar - File and device selection
        top_bar = QHBoxLayout()
        
        self.load_btn = QPushButton("📂 Add Track")
        self.load_btn.clicked.connect(self.add_track)
        top_bar.addWidget(self.load_btn)
        
        self.load_cslp_btn = QPushButton("📄 CSLP")
        self.load_cslp_btn.clicked.connect(self.load_cslp_file)
        top_bar.addWidget(self.load_cslp_btn)
        
        self.file_label = QLabel("No tracks loaded")
        self.file_label.setStyleSheet("color: #888888;")
        top_bar.addWidget(self.file_label, 1)
        
        top_bar.addWidget(QLabel("Master:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.populate_devices()
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        top_bar.addWidget(self.device_combo)
        
        layout.addLayout(top_bar)
        
        # Lyrics/Notation display
        self.lyrics_display = LyricsDisplayWidget()
        layout.addWidget(self.lyrics_display)
        
        # Tracks scroll area
        tracks_group = QGroupBox("Tracks")
        tracks_layout = QVBoxLayout(tracks_group)
        tracks_layout.setContentsMargins(5, 15, 5, 5)
        
        self.tracks_scroll = QScrollArea()
        self.tracks_scroll.setWidgetResizable(True)
        self.tracks_scroll.setMinimumHeight(100)
        self.tracks_scroll.setMaximumHeight(250)
        self.tracks_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.tracks_container = QWidget()
        self.tracks_container_layout = QVBoxLayout(self.tracks_container)
        self.tracks_container_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_container_layout.setSpacing(5)
        self.tracks_container_layout.addStretch()
        
        self.tracks_scroll.setWidget(self.tracks_container)
        tracks_layout.addWidget(self.tracks_scroll)
        
        layout.addWidget(tracks_group)
        
        # Main waveform display (first track)
        self.waveform = WaveformWidget()
        self.waveform.position_clicked.connect(self.on_waveform_click)
        self.waveform.loop_changed.connect(self.on_loop_changed)
        layout.addWidget(self.waveform, 1)
        
        # Markers display
        self.markers_widget = MarkersWidget()
        self.markers_widget.marker_clicked.connect(self.on_marker_clicked)
        layout.addWidget(self.markers_widget)
        
        # Time display
        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00.00 / 00:00.00")
        self.time_label.setStyleSheet("font-size: 18px; font-family: monospace;")
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
        
        transport.addStretch()
        layout.addLayout(transport)
        
        # Status bar
        self.status_label = QLabel("Ready. Load an audio file to begin.")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.status_label)
    
    def populate_devices(self):
        """Populate device dropdown with available output devices."""
        self.device_combo.clear()
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
                self.device_combo.addItem(name, i)
                self.available_devices.append((name, i))
                
                if i == default_output:
                    self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.on_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.on_stop)
        QShortcut(QKeySequence("Ctrl+O"), self, self.add_track)
        QShortcut(QKeySequence(Qt.Key.Key_L), self, lambda: self.loop_btn.click())
    
    def setup_timer(self):
        """Setup timer for UI updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(30)  # ~33fps update
    
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
            self.waveform.set_audio_data(None)
            self.file_label.setText("No tracks loaded")
        else:
            self.file_label.setText(f"{len(self.engine.tracks)} track(s)")
            # Update waveform with first remaining track
            self.waveform.set_audio_data(self.engine.tracks[0].audio_data)
        
        self.status_label.setText(f"Removed track {track_id}")
    
    def on_track_changed(self, track_id):
        """Handle track settings changed (mute/solo/volume)."""
        pass  # Settings already applied to track object
    
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
        
        if success and self.cslp_data.timeline:
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
            self.status_label.setText("CSLP file has no markers")
    
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
    
    def on_device_changed(self, index):
        """Handle device selection change."""
        device_index = self.device_combo.currentData()
        if device_index is not None:
            self.engine.set_device(device_index)
            device_name = self.device_combo.currentText()
            self.status_label.setText(f"Output: {device_name}")
    
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
    
    def on_loop_toggle(self):
        """Handle loop toggle."""
        enabled = self.loop_btn.isChecked()
        
        if enabled and self.engine.tracks:
            # Set loop to full track for now (use first track's length)
            total_samples = self.engine.get_total_samples()
            self.engine.set_loop(True, 0, total_samples)
            self.waveform.set_loop(True, 0, 1)
            self.status_label.setText("Loop enabled (full track)")
        else:
            self.engine.set_loop(False)
            self.waveform.set_loop(False)
            self.status_label.setText("Loop disabled")
    
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
            
            # Update status with loop times
            start_sec = start_samples / self.engine.sample_rate
            end_sec = end_samples / self.engine.sample_rate
            self.status_label.setText(
                f"Loop: {int(start_sec//60):02d}:{start_sec%60:05.2f} → "
                f"{int(end_sec//60):02d}:{end_sec%60:05.2f}"
            )
    
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
    
    def closeEvent(self, event):
        """Clean up on close."""
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
