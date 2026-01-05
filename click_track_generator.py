#!/usr/bin/env python3
"""
Click Track Generator
Creates click tracks from CSLP timestamp files with woodblock sounds.
"""

import sys
import json
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess


class ClickTrackGenerator(QThread):
    """Worker thread for generating click tracks."""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, audio_file, cslp_file, output_file):
        super().__init__()
        self.audio_file = audio_file
        self.cslp_file = cslp_file
        self.output_file = output_file

    def generate_woodblock_click(self, sample_rate=44100, duration=0.1):
        """Generate a woodblock-like click sound."""
        # Create a short impulse with some harmonics
        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # Fundamental frequency (around 2000 Hz for woodblock sound)
        freq = 2000

        # Create woodblock-like sound with multiple harmonics
        click = (
            0.8 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 50) +  # Fundamental
            0.4 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 60) +  # 2nd harmonic
            0.2 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t * 70)    # 3rd harmonic
        )

        # Apply envelope for attack/decay
        envelope = np.exp(-t * 30)  # Quick decay
        click *= envelope

        # Normalize
        click = click / np.max(np.abs(click)) * 0.8

        return click

    def run(self):
        """Generate the click track."""
        try:
            self.progress_updated.emit(0, "Loading audio file...")

            # Load audio file to get duration and sample rate
            audio_info = sf.info(self.audio_file)
            duration = audio_info.duration
            sample_rate = audio_info.samplerate

            self.progress_updated.emit(10, f"Audio duration: {duration:.2f}s, Sample rate: {sample_rate}Hz")

            # Load CSLP file
            self.progress_updated.emit(20, "Loading CSLP file...")
            with open(self.cslp_file, 'r', encoding='utf-8') as f:
                cslp_data = json.load(f)

            timeline = cslp_data.get('data', {}).get('timeline', [])
            if not timeline:
                self.finished.emit(False, "No timeline data found in CSLP file")
                return

            self.progress_updated.emit(30, f"Found {len(timeline)} timestamps")

            # Generate click sound
            self.progress_updated.emit(40, "Generating woodblock click sound...")
            click_sound = self.generate_woodblock_click(sample_rate)

            # Create silent audio track of same length as original
            total_samples = int(duration * sample_rate)
            click_track = np.zeros(total_samples)

            # Add clicks at each timestamp
            click_count = 0
            for i, entry in enumerate(timeline):
                timestamp = entry.get('time', 0)
                if timestamp >= 0 and timestamp <= duration:
                    # Calculate sample position
                    sample_pos = int(timestamp * sample_rate)

                    # Ensure we don't go beyond array bounds
                    end_pos = min(sample_pos + len(click_sound), len(click_track))
                    click_len = end_pos - sample_pos

                    if click_len > 0:
                        click_track[sample_pos:end_pos] += click_sound[:click_len]
                        click_count += 1

                progress = 40 + int((i / len(timeline)) * 50)
                self.progress_updated.emit(progress, f"Adding click {i+1}/{len(timeline)} at {timestamp:.2f}s")

            self.progress_updated.emit(90, f"Added {click_count} clicks. Saving file...")

            # Save the click track
            sf.write(self.output_file, click_track, sample_rate)

            self.progress_updated.emit(100, "Click track generated successfully!")
            self.finished.emit(True, f"Generated click track with {click_count} clicks")

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class ClickTrackGeneratorApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.audio_file = None
        self.cslp_file = None
        self.generator = None

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Click Track Generator")
        self.setGeometry(300, 300, 600, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # File selection section
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)

        # Audio file selection
        audio_layout = QHBoxLayout()
        self.audio_label = QLabel("No audio file selected")
        audio_btn = QPushButton("Select Audio File")
        audio_btn.clicked.connect(self.select_audio_file)
        audio_layout.addWidget(QLabel("Audio:"))
        audio_layout.addWidget(self.audio_label)
        audio_layout.addWidget(audio_btn)
        file_layout.addLayout(audio_layout)

        # CSLP file selection
        cslp_layout = QHBoxLayout()
        self.cslp_label = QLabel("No CSLP file selected")
        cslp_btn = QPushButton("Select CSLP File")
        cslp_btn.clicked.connect(self.select_cslp_file)
        cslp_layout.addWidget(QLabel("CSLP:"))
        cslp_layout.addWidget(self.cslp_label)
        cslp_layout.addWidget(cslp_btn)
        file_layout.addLayout(cslp_layout)

        layout.addWidget(file_group)

        # Generate section
        generate_group = QGroupBox("Generate Click Track")
        generate_layout = QVBoxLayout(generate_group)

        self.generate_btn = QPushButton("🎵 Generate Click Track")
        self.generate_btn.clicked.connect(self.generate_click_track)
        self.generate_btn.setEnabled(False)
        generate_layout.addWidget(self.generate_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        generate_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        generate_layout.addWidget(self.status_label)

        layout.addWidget(generate_group)

        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.append("Click Track Generator ready.\nSelect audio and CSLP files to begin.")
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

    def select_audio_file(self):
        """Select audio file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.aac);;All Files (*.*)"
        )

        if filepath:
            self.audio_file = filepath
            self.audio_label.setText(Path(filepath).name)
            self.check_generate_enabled()

    def select_cslp_file(self):
        """Select CSLP file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSLP File",
            "",
            "CSLP Files (*.cslp);;JSON Files (*.json);;All Files (*.*)"
        )

        if filepath:
            self.cslp_file = filepath
            self.cslp_label.setText(Path(filepath).name)
            self.check_generate_enabled()

    def check_generate_enabled(self):
        """Enable generate button if both files are selected."""
        self.generate_btn.setEnabled(self.audio_file is not None and self.cslp_file is not None)

    def generate_click_track(self):
        """Generate the click track."""
        if not self.audio_file or not self.cslp_file:
            return

        # Generate output filename
        audio_basename = Path(self.audio_file).stem
        default_output = f"{audio_basename}_click_track.mp3"

        # Ask user for output location
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Click Track",
            default_output,
            "MP3 Files (*.mp3);;WAV Files (*.wav);;All Files (*.*)"
        )

        if not output_file:
            return

        # Disable generate button and show progress
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Generating click track...")

        # Start generation in background thread
        self.generator = ClickTrackGenerator(self.audio_file, self.cslp_file, output_file)
        self.generator.progress_updated.connect(self.update_progress)
        self.generator.finished.connect(self.generation_finished)
        self.generator.start()

    def update_progress(self, value, message):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log_text.append(message)

    def generation_finished(self, success, message):
        """Handle generation completion."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)

        if success:
            self.status_label.setText("Click track generated successfully!")
            self.log_text.append(f"✅ {message}")
        else:
            self.status_label.setText("Generation failed")
            self.log_text.append(f"❌ {message}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = ClickTrackGeneratorApp()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()