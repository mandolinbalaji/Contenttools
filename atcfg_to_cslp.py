#!/usr/bin/env python3
"""
ATCFG to CSLP Converter
Convert Anytune .atcfg files to CSLP format for precision playback.

Features:
- Load .atcfg files with timing data
- Extract metadata and audio marks
- Add lyrics and notation for each timestamp
- Generate CSLP JSON format
- Save CSLP files for use with precision player
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, QGroupBox,
    QFormLayout, QScrollArea, QFrame, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon


class ATCFGToCSLPConverter(QMainWindow):
    """Main window for ATCFG to CSLP conversion."""

    def __init__(self):
        super().__init__()
        self.atcfg_data = None
        self.base_name = ""
        self.timeline_entries = []
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("ATCFG to CSLP Converter")
        self.setMinimumSize(1000, 800)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
            }
            QLabel {
                color: #ecf0f1;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
            QLineEdit, QTextEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #5dade2;
            }
            QGroupBox {
                color: #ecf0f1;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                font-size: 16px;
                font-weight: bold;
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
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎵 ATCFG to CSLP Converter")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ecf0f1; margin-bottom: 10px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # File selection
        file_group = QGroupBox("📁 File Selection")
        file_layout = QHBoxLayout(file_group)

        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #95a5a6; font-style: italic;")
        file_layout.addWidget(self.file_path_label)

        load_btn = QPushButton("Load .atcfg File")
        load_btn.clicked.connect(self.load_atcfg_file)
        file_layout.addWidget(load_btn)

        layout.addWidget(file_group)

        # Metadata section
        metadata_group = QGroupBox("📋 Song Metadata")
        metadata_layout = QFormLayout(metadata_group)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Song title")
        metadata_layout.addRow("Title:", self.title_edit)

        self.artist_edit = QLineEdit()
        self.artist_edit.setPlaceholderText("Artist name")
        metadata_layout.addRow("Artist:", self.artist_edit)

        self.ragam_edit = QLineEdit()
        self.ragam_edit.setPlaceholderText("e.g., Kharaharapriya")
        metadata_layout.addRow("Ragam:", self.ragam_edit)

        self.talam_edit = QLineEdit()
        self.talam_edit.setPlaceholderText("e.g., Adi")
        metadata_layout.addRow("Talam:", self.talam_edit)

        self.shruti_edit = QLineEdit()
        self.shruti_edit.setPlaceholderText("e.g., C, C#")
        metadata_layout.addRow("Shruti:", self.shruti_edit)

        self.aarohanam_edit = QLineEdit()
        self.aarohanam_edit.setPlaceholderText("e.g., S R2 G2 M1 P D2 N2 S")
        metadata_layout.addRow("Aarohanam:", self.aarohanam_edit)

        self.avarohanam_edit = QLineEdit()
        self.avarohanam_edit.setPlaceholderText("e.g., S N2 D2 P M1 G2 R2 S")
        metadata_layout.addRow("Avarohanam:", self.avarohanam_edit)

        self.edupu_edit = QLineEdit()
        self.edupu_edit.setText("60")
        self.edupu_edit.setPlaceholderText("BPM")
        metadata_layout.addRow("Edupu (BPM):", self.edupu_edit)

        self.mp3_edit = QLineEdit()
        self.mp3_edit.setPlaceholderText("song.mp3")
        metadata_layout.addRow("MP3 Filename:", self.mp3_edit)

        layout.addWidget(metadata_group)

        # Timeline section
        timeline_group = QGroupBox("⏰ Timeline & Lyrics")
        timeline_layout = QVBoxLayout(timeline_group)

        # Scroll area for timeline entries
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.timeline_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        timeline_layout.addWidget(scroll_area)

        layout.addWidget(timeline_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.preview_btn = QPushButton("👁️ Preview CSLP")
        self.preview_btn.clicked.connect(self.preview_cslp)
        self.preview_btn.setEnabled(False)
        button_layout.addWidget(self.preview_btn)

        self.save_btn = QPushButton("💾 Save CSLP")
        self.save_btn.clicked.connect(self.save_cslp)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        layout.addWidget(self.status_label)

    def load_atcfg_file(self):
        """Load an ATCFG file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ATCFG File", "", "ATCFG Files (*.atcfg);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.atcfg_data = json.load(f)

            self.base_name = Path(file_path).stem
            self.file_path_label.setText(f"Loaded: {Path(file_path).name}")
            self.file_path_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            # Populate metadata
            self.populate_metadata()

            # Create timeline
            self.create_timeline()

            # Enable buttons
            self.preview_btn.setEnabled(True)
            self.save_btn.setEnabled(True)

            self.status_label.setText("ATCFG file loaded successfully!")
            self.status_label.setStyleSheet("color: #27ae60;")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load ATCFG file:\n{str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c;")

    def populate_metadata(self):
        """Populate metadata fields from ATCFG data."""
        if not self.atcfg_data or 'trackData' not in self.atcfg_data:
            return

        track = self.atcfg_data['trackData'][0]

        self.title_edit.setText(track.get('title', self.base_name))
        self.artist_edit.setText(track.get('artist', ''))
        self.mp3_edit.setText(self.base_name + '.mp3')

    def create_timeline(self):
        """Create timeline entries from audio marks."""
        # Clear existing timeline
        while self.timeline_layout.count():
            child = self.timeline_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.atcfg_data or 'trackData' not in self.atcfg_data:
            return

        audio_marks = self.atcfg_data['trackData'][0].get('audioMarks', [])

        self.timeline_entries = []

        for i, mark in enumerate(audio_marks):
            # Create timeline entry widget
            entry_widget = QFrame()
            entry_widget.setFrameStyle(QFrame.Shape.Box)
            entry_widget.setStyleSheet("""
                QFrame {
                    background-color: #34495e;
                    border: 1px solid #3498db;
                    border-radius: 4px;
                    margin: 5px 0;
                }
            """)

            entry_layout = QHBoxLayout(entry_widget)

            # Time label
            time_label = QLabel(f"{mark['time']:.2f}s")
            time_label.setStyleSheet("color: #3498db; font-weight: bold; min-width: 80px;")
            entry_layout.addWidget(time_label)

            # Lyrics input
            lyrics_edit = QLineEdit()
            lyrics_edit.setPlaceholderText("Enter lyrics for this timestamp")
            entry_layout.addWidget(lyrics_edit)

            # Notation input
            notation_edit = QLineEdit()
            notation_edit.setPlaceholderText("Notation (optional)")
            notation_edit.setMaximumWidth(150)
            entry_layout.addWidget(notation_edit)

            self.timeline_layout.addWidget(entry_widget)

            # Store references
            self.timeline_entries.append({
                'time': mark['time'],
                'lyrics_edit': lyrics_edit,
                'notation_edit': notation_edit
            })

    def preview_cslp(self):
        """Generate and preview CSLP content."""
        try:
            cslp_data = self.generate_cslp_data()

            # Show preview dialog
            preview_dialog = QMessageBox(self)
            preview_dialog.setWindowTitle("CSLP Preview")
            preview_dialog.setText("CSLP JSON Preview:")
            preview_dialog.setDetailedText(json.dumps(cslp_data, indent=2, ensure_ascii=False))

            # Make the detailed text scrollable
            scroll_area = preview_dialog.findChild(QTextEdit)
            if scroll_area:
                scroll_area.setMaximumHeight(400)

            preview_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate CSLP preview:\n{str(e)}")

    def save_cslp(self):
        """Generate and save CSLP file."""
        try:
            cslp_data = self.generate_cslp_data()

            # Get save location
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save CSLP File", f"{self.base_name}.cslp", "CSLP Files (*.cslp);;JSON Files (*.json)"
            )

            if not save_path:
                return

            # Save file
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(cslp_data, f, indent=2, ensure_ascii=False)

            self.status_label.setText(f"CSLP file saved: {Path(save_path).name}")
            self.status_label.setStyleSheet("color: #27ae60;")

            QMessageBox.information(self, "Success", f"CSLP file saved successfully!\n\n{Path(save_path).name}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSLP file:\n{str(e)}")
            self.status_label.setText(f"Save error: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c;")

    def generate_cslp_data(self):
        """Generate CSLP data structure."""
        if not self.atcfg_data:
            raise ValueError("No ATCFG data loaded")

        # Collect metadata
        metadata = {
            'title': self.title_edit.text() or self.base_name,
            'artist': self.artist_edit.text(),
            'ragam': self.ragam_edit.text(),
            'talam': self.talam_edit.text(),
            'shruti': self.shruti_edit.text(),
            'aarohanam': self.aarohanam_edit.text(),
            'avarohanam': self.avarohanam_edit.text(),
            'edupu': int(self.edupu_edit.text() or 60)
        }

        # Generate timeline
        timeline = []
        ulp_lines = []

        for i, entry in enumerate(self.timeline_entries):
            lyrics = entry['lyrics_edit'].text()
            notation = entry['notation_edit'].text()

            timeline.append({
                'id': int(datetime.now().timestamp() * 1000) + i,
                'time': entry['time'],
                'text': lyrics,
                'notation': notation,
                'lineNumber': i
            })

            ulp_lines.append(lyrics)

        # Calculate last position
        last_position = max((entry['time'] for entry in self.timeline_entries), default=0)

        # Generate CSLP structure
        cslp_data = {
            'data': {
                'metadata': metadata,
                'mp3FileName': self.mp3_edit.text(),
                'config': {
                    'offset': 0.25,
                    'lastPosition': last_position
                },
                'ulpLines': ulp_lines,
                'rawText': '\n'.join(ulp_lines),
                'timeline': timeline
            },
            'integrityHash': self.generate_hash()
        }

        return cslp_data

    def generate_hash(self):
        """Generate a simple integrity hash."""
        import hashlib
        import time
        data = f"{self.base_name}{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Set application properties
    app.setApplicationName("ATCFG to CSLP Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Balaji's Tools")

    # Create and show main window
    window = ATCFGToCSLPConverter()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()