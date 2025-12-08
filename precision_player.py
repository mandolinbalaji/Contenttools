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
    QSplitter, QGroupBox, QScrollArea
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
            if self.loop_enabled and end_pos >= self.loop_end:
                # Need to wrap around
                samples_before_loop = self.loop_end - self.position
                samples_after_loop = frames - samples_before_loop
                
                if samples_before_loop > 0:
                    outdata[:samples_before_loop] = self.audio_data[self.position:self.loop_end]
                
                # Wrap to loop start
                self.position = self.loop_start
                
                if samples_after_loop > 0:
                    end_after = self.position + samples_after_loop
                    outdata[samples_before_loop:] = self.audio_data[self.position:end_after]
                    self.position = end_after
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
            # Don't let start go past end
            self.loop_start_ratio = min(ratio, self.loop_end_ratio - 0.01)
            self.update()
            self.loop_changed.emit(self.loop_start_ratio, self.loop_end_ratio)
        elif self.dragging == 'end':
            # Don't let end go before start
            self.loop_end_ratio = max(ratio, self.loop_start_ratio + 0.01)
            self.update()
            self.loop_changed.emit(self.loop_start_ratio, self.loop_end_ratio)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.dragging = None


class PrecisionPlayer(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.engine = AudioEngine()
        self.cslp_data = CSLPData()
        self.current_file = None
        self.current_cslp = None
        
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
        
        self.load_btn = QPushButton("📂 Audio")
        self.load_btn.clicked.connect(self.load_file)
        top_bar.addWidget(self.load_btn)
        
        self.load_cslp_btn = QPushButton("📄 CSLP")
        self.load_cslp_btn.clicked.connect(self.load_cslp_file)
        top_bar.addWidget(self.load_cslp_btn)
        
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #888888;")
        top_bar.addWidget(self.file_label, 1)
        
        top_bar.addWidget(QLabel("Output:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.populate_devices()
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        top_bar.addWidget(self.device_combo)
        
        layout.addLayout(top_bar)
        
        # Lyrics/Notation display
        self.lyrics_display = LyricsDisplayWidget()
        layout.addWidget(self.lyrics_display)
        
        # Waveform display
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
                
                if i == default_output:
                    self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.on_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.on_stop)
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_file)
        QShortcut(QKeySequence(Qt.Key.Key_L), self, lambda: self.loop_btn.click())
    
    def setup_timer(self):
        """Setup timer for UI updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(30)  # ~33fps update
    
    def load_file(self):
        """Open file dialog and load audio."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;All Files (*.*)"
        )
        
        if filepath:
            self.status_label.setText(f"Loading: {filepath}")
            QApplication.processEvents()
            
            success, message = self.engine.load_file(filepath)
            
            if success:
                self.current_file = Path(filepath)
                self.file_label.setText(self.current_file.name)
                self.waveform.set_audio_data(self.engine.audio_data)
                self.play_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                self.status_label.setText(message)
                
                # Auto-load CSLP if exists with same name
                cslp_path = self.current_file.with_suffix('.cslp')
                if cslp_path.exists():
                    self.load_cslp_from_path(str(cslp_path))
            else:
                self.status_label.setText(f"Error: {message}")
    
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
            self.markers_widget.set_markers(
                self.cslp_data.timeline,
                self.engine.get_duration() if self.engine.audio_data is not None else 0
            )
            self.status_label.setText(
                f"Loaded CSLP: {len(self.cslp_data.timeline)} markers"
            )
        else:
            self.status_label.setText("CSLP file has no markers")
    
    def on_marker_clicked(self, time_seconds):
        """Handle click on a marker - jump to that position."""
        if self.engine.audio_data is not None:
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
        if self.engine.audio_data is None:
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
        
        if enabled and self.engine.audio_data is not None:
            # Set loop to full track for now
            self.engine.set_loop(True, 0, len(self.engine.audio_data))
            self.waveform.set_loop(True, 0, 1)
            self.status_label.setText("Loop enabled (full track)")
        else:
            self.engine.set_loop(False)
            self.waveform.set_loop(False)
            self.status_label.setText("Loop disabled")
    
    def on_waveform_click(self, ratio):
        """Handle click on waveform to seek."""
        if self.engine.audio_data is not None:
            total_samples = len(self.engine.audio_data)
            self.engine.set_position_samples(ratio * total_samples)
    
    def on_loop_changed(self, start_ratio, end_ratio):
        """Handle loop markers being dragged."""
        if self.engine.audio_data is not None:
            total_samples = len(self.engine.audio_data)
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
        if self.engine.audio_data is not None:
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
