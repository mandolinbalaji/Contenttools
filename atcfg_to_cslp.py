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
    QFormLayout, QScrollArea, QFrame, QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon


class ATCFGToCSLPConverter(QMainWindow):
    """Main window for ATCFG to CSLP conversion."""

    def __init__(self):
        super().__init__()
        self.atcfg_data = None
        self.cslp_data = None
        self.base_name = ""
        self.timeline_entries = []
        self.current_file_type = None  # 'atcfg' or 'cslp'
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

        load_atcfg_btn = QPushButton("Load .atcfg")
        load_atcfg_btn.clicked.connect(self.load_atcfg_file)
        file_layout.addWidget(load_atcfg_btn)

        load_cslp_btn = QPushButton("Load .cslp")
        load_cslp_btn.clicked.connect(self.load_cslp_file)
        file_layout.addWidget(load_cslp_btn)

        file_layout.addStretch()

        layout.addWidget(file_group)

        layout.addWidget(file_group)

        # Metadata section
        self.metadata_group = QGroupBox("📋 Song Metadata")
        metadata_layout = QVBoxLayout(self.metadata_group)
        self.metadata_group.setVisible(False)

        # Create metadata table with 2 columns for better layout
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(4)  # 2 columns for labels, 2 for inputs
        self.metadata_table.setHorizontalHeaderLabels(["Field 1", "Value 1", "Field 2", "Value 2"])
        self.metadata_table.horizontalHeader().setStretchLastSection(True)
        self.metadata_table.setAlternatingRowColors(True)
        self.metadata_table.setStyleSheet("""
            QTableWidget {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: #ecf0f1;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #34495e;
            }
            QLineEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px;
            }
        """)

        # Add metadata rows in 2-column layout
        metadata_fields_left = [
            ("Title", "title_edit"),
            ("Artist", "artist_edit"),
            ("Ragam", "ragam_edit"),
            ("Talam", "talam_edit"),
            ("Edupu (BPM)", "edupu_edit")
        ]

        metadata_fields_right = [
            ("Shruti", "shruti_edit"),
            ("Aarohanam", "aarohanam_edit"),
            ("Avarohanam", "avarohanam_edit"),
            ("MP3 Filename", "mp3_edit")
        ]

        # Calculate number of rows needed (max of both columns)
        num_rows = max(len(metadata_fields_left), len(metadata_fields_right))
        self.metadata_table.setRowCount(num_rows)

        # Fill left column
        for row, (label_text, attr_name) in enumerate(metadata_fields_left):
            # Label
            label_item = QTableWidgetItem(label_text)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.metadata_table.setItem(row, 0, label_item)

            # Input widget
            input_widget = QLineEdit()
            if attr_name == "edupu_edit":
                input_widget.setText("60")
            input_widget.setPlaceholderText(f"Enter {label_text.lower()}")
            input_widget.setMinimumHeight(30)
            setattr(self, attr_name, input_widget)
            self.metadata_table.setCellWidget(row, 1, input_widget)

        # Fill right column
        for row, (label_text, attr_name) in enumerate(metadata_fields_right):
            # Label
            label_item = QTableWidgetItem(label_text)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.metadata_table.setItem(row, 2, label_item)

            # Input widget
            input_widget = QLineEdit()
            input_widget.setPlaceholderText(f"Enter {label_text.lower()}")
            input_widget.setMinimumHeight(30)
            setattr(self, attr_name, input_widget)
            self.metadata_table.setCellWidget(row, 3, input_widget)

        self.metadata_table.resizeColumnsToContents()
        # Set minimum row height for better visibility
        for i in range(self.metadata_table.rowCount()):
            self.metadata_table.setRowHeight(i, 35)
        metadata_layout.addWidget(self.metadata_table)

        layout.addWidget(self.metadata_group)

        # Timeline section
        self.timeline_group = QGroupBox("⏰ Timeline & Lyrics")
        timeline_layout = QVBoxLayout(self.timeline_group)
        self.timeline_group.setVisible(False)

        # Create timeline table
        self.timeline_table = QTableWidget()
        self.timeline_table.setColumnCount(3)
        self.timeline_table.setHorizontalHeaderLabels(["Time (s)", "Lyrics", "Notation"])
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_table.setAlternatingRowColors(True)
        self.timeline_table.setStyleSheet("""
            QTableWidget {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: #ecf0f1;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #34495e;
            }
            QLineEdit {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 5px;
            }
        """)

        # Set minimum height for the table
        self.timeline_table.setMinimumHeight(400)

        # Set minimum row height for better visibility
        for i in range(self.timeline_table.rowCount()):
            self.timeline_table.setRowHeight(i, 35)

        timeline_layout.addWidget(self.timeline_table)

        layout.addWidget(self.timeline_group)

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
            self.current_file_type = 'atcfg'
            self.file_path_label.setText(f"Loaded ATCFG: {Path(file_path).name}")
            self.file_path_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.setWindowTitle(f"ATCFG to CSLP Converter - Editing: {Path(file_path).name}")

            # Populate metadata
            self.populate_metadata()

            # Create timeline
            self.create_timeline()

            # Show sections
            self.metadata_group.setVisible(True)
            self.timeline_group.setVisible(True)

            # Enable buttons
            self.preview_btn.setEnabled(True)
            self.save_btn.setEnabled(True)

            self.status_label.setText("ATCFG file loaded successfully!")
            self.status_label.setStyleSheet("color: #27ae60;")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load ATCFG file:\n{str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c;")

    def load_cslp_file(self):
        """Load an existing CSLP file for editing."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSLP File", "", "CSLP Files (*.cslp);;JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.cslp_data = json.load(f)

            self.base_name = Path(file_path).stem
            self.current_file_type = 'cslp'
            self.file_path_label.setText(f"Loaded CSLP: {Path(file_path).name}")
            self.file_path_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.setWindowTitle(f"ATCFG to CSLP Converter - Editing: {Path(file_path).name}")

            # Populate metadata from CSLP
            self.populate_metadata_from_cslp()

            # Create timeline from CSLP
            self.create_timeline_from_cslp()

            # Show sections
            self.metadata_group.setVisible(True)
            self.timeline_group.setVisible(True)
            self.preview_btn.setEnabled(True)
            self.save_btn.setEnabled(True)

            self.status_label.setText("CSLP file loaded successfully!")
            self.status_label.setStyleSheet("color: #27ae60;")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSLP file:\n{str(e)}")
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

    def populate_metadata_from_cslp(self):
        """Populate metadata fields from CSLP data."""
        if not self.cslp_data or 'data' not in self.cslp_data:
            return

        metadata = self.cslp_data['data'].get('metadata', {})
        config = self.cslp_data['data'].get('config', {})

        self.title_edit.setText(metadata.get('title', self.base_name))
        self.artist_edit.setText(metadata.get('artist', ''))
        self.ragam_edit.setText(metadata.get('ragam', ''))
        self.talam_edit.setText(metadata.get('talam', ''))
        self.shruti_edit.setText(metadata.get('shruti', ''))
        self.aarohanam_edit.setText(metadata.get('aarohanam', ''))
        self.avarohanam_edit.setText(metadata.get('avarohanam', ''))
        self.edupu_edit.setText(str(metadata.get('edupu', 60)))
        self.mp3_edit.setText(self.cslp_data['data'].get('mp3FileName', ''))

    def create_timeline(self):
        """Create timeline entries from ATCFG audio marks."""
        if not self.atcfg_data or 'trackData' not in self.atcfg_data:
            return

        audio_marks = self.atcfg_data['trackData'][0].get('audioMarks', [])
        self.timeline_table.setRowCount(len(audio_marks))
        self.timeline_entries = []

        for row, mark in enumerate(audio_marks):
            # Time column
            time_item = QTableWidgetItem(f"{mark['time']:.6f}")
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.timeline_table.setItem(row, 0, time_item)

            # Lyrics column
            lyrics_edit = QLineEdit()
            lyrics_edit.setPlaceholderText("Enter lyrics for this timestamp")
            lyrics_edit.setMinimumHeight(30)  # Increase field height
            self.timeline_table.setCellWidget(row, 1, lyrics_edit)

            # Notation column
            notation_edit = QLineEdit()
            notation_edit.setPlaceholderText("Notation (optional)")
            notation_edit.setMaximumWidth(150)
            notation_edit.setMinimumHeight(30)  # Increase field height
            self.timeline_table.setCellWidget(row, 2, notation_edit)

            # Store references for later use
            self.timeline_entries.append({
                'time': mark['time'],
                'lyrics_edit': lyrics_edit,
                'notation_edit': notation_edit
            })

        self.timeline_table.resizeColumnsToContents()
        # Set proportional column widths: Time (10%), Lyrics (45%), Notation (stretches to fill remaining)
        table_width = self.timeline_table.width()
        if table_width > 0:
            self.timeline_table.setColumnWidth(0, int(table_width * 0.10))  # Time column (smaller)
            self.timeline_table.setColumnWidth(1, int(table_width * 0.45))  # Lyrics column
            # Column 2 (Notation) will stretch to fill remaining space due to setStretchLastSection(True)
        else:
            # Fallback widths if table width not available yet
            self.timeline_table.setColumnWidth(0, 80)    # Time
            self.timeline_table.setColumnWidth(1, 285)   # Lyrics (45% of ~630px)
            # Column 2 (Notation) will stretch to fill remaining space

        # Set minimum row height for better visibility
        for i in range(len(audio_marks)):
            self.timeline_table.setRowHeight(i, 35)

    def create_timeline_from_cslp(self):
        """Create timeline entries from CSLP timeline data."""
        if not self.cslp_data or 'data' not in self.cslp_data:
            return

        timeline = self.cslp_data['data'].get('timeline', [])
        self.timeline_table.setRowCount(len(timeline))
        self.timeline_entries = []

        for row, item in enumerate(timeline):
            # Time column
            time_item = QTableWidgetItem(f"{item['time']:.6f}")
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.timeline_table.setItem(row, 0, time_item)

            # Lyrics column (pre-filled from CSLP)
            lyrics_edit = QLineEdit()
            lyrics_edit.setText(item.get('text', ''))
            lyrics_edit.setPlaceholderText("Enter lyrics for this timestamp")
            lyrics_edit.setMinimumHeight(30)  # Increase field height
            self.timeline_table.setCellWidget(row, 1, lyrics_edit)

            # Notation column (pre-filled from CSLP)
            notation_edit = QLineEdit()
            notation_edit.setText(item.get('notation', ''))
            notation_edit.setPlaceholderText("Notation (optional)")
            notation_edit.setMaximumWidth(150)
            notation_edit.setMinimumHeight(30)  # Increase field height
            self.timeline_table.setCellWidget(row, 2, notation_edit)

            # Store references for later use
            self.timeline_entries.append({
                'time': item['time'],
                'lyrics_edit': lyrics_edit,
                'notation_edit': notation_edit
            })

        self.timeline_table.resizeColumnsToContents()
        # Set proportional column widths: Time (10%), Lyrics (45%), Notation (stretches to fill remaining)
        table_width = self.timeline_table.width()
        if table_width > 0:
            self.timeline_table.setColumnWidth(0, int(table_width * 0.10))  # Time column (smaller)
            self.timeline_table.setColumnWidth(1, int(table_width * 0.45))  # Lyrics column
            # Column 2 (Notation) will stretch to fill remaining space due to setStretchLastSection(True)
        else:
            # Fallback widths if table width not available yet
            self.timeline_table.setColumnWidth(0, 80)    # Time
            self.timeline_table.setColumnWidth(1, 285)   # Lyrics (45% of ~630px)
            # Column 2 (Notation) will stretch to fill remaining space

        # Set minimum row height for better visibility
        for i in range(len(timeline)):
            self.timeline_table.setRowHeight(i, 35)

    def preview_cslp(self):
        """Generate and preview CSLP content."""
        try:
            cslp_data = self.generate_cslp_data()

            # Create custom preview dialog
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle("CSLP Preview")
            preview_dialog.setMinimumSize(800, 600)  # Much larger dialog
            preview_dialog.setModal(True)

            layout = QVBoxLayout(preview_dialog)

            # Title label
            title_label = QLabel("CSLP JSON Preview:")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
            layout.addWidget(title_label)

            # Text area for JSON preview
            preview_text = QTextEdit()
            preview_text.setPlainText(json.dumps(cslp_data, indent=2, ensure_ascii=False))
            preview_text.setFont(QFont("Consolas", 10))  # Monospace font for JSON
            preview_text.setReadOnly(True)
            preview_text.setMinimumHeight(500)  # Tall text area
            layout.addWidget(preview_text)

            # Button box
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(preview_dialog.reject)
            layout.addWidget(button_box)

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