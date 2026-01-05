#!/usr/bin/env python3
"""
Project Dialog for Precision Player
UI for managing projects (create, load, save, list).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QInputDialog,
    QWidget, QSplitter, QTextEdit, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class ProjectDialog(QDialog):
    """Dialog for managing projects."""

    project_selected = pyqtSignal(dict)  # Emits project data when selected

    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.selected_project = None

        self.setWindowTitle("Project Manager")
        self.setModal(True)
        self.resize(700, 500)

        self.setup_ui()
        self.load_projects()

    def setup_ui(self):
        """Setup the user interface."""
        # Apply dark theme stylesheet
        self.setStyleSheet("""
            QDialog {
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
                padding: 8px 16px;
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 500;
                min-height: 16px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a5568, stop:1 #2d3748);
                border-color: #63b3ed;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a202c, stop:1 #0f0f23);
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
                border-color: #444;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a5568;
                border-radius: 6px;
                margin-top: 1ex;
                color: #e6e6e6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #e6e6e6;
                font-weight: bold;
            }
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #4a5568;
                border-radius: 4px;
                color: #e6e6e6;
                selection-background-color: #4a5568;
            }
            QListWidget::item:hover {
                background-color: #2d3748;
            }
            QListWidget::item:selected {
                background-color: #4a5568;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Precision Player Projects")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Projects list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Projects list header
        list_header = QLabel("Available Projects")
        list_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_layout.addWidget(list_header)

        self.projects_list = QListWidget()
        self.projects_list.itemDoubleClicked.connect(self.on_project_double_clicked)
        self.projects_list.itemSelectionChanged.connect(self.on_project_selected)
        left_layout.addWidget(self.projects_list)

        # Project action buttons
        buttons_layout = QHBoxLayout()

        self.new_btn = QPushButton("New Project")
        self.new_btn.clicked.connect(self.create_new_project)
        buttons_layout.addWidget(self.new_btn)

        self.load_btn = QPushButton("Load Selected")
        self.load_btn.clicked.connect(self.load_selected_project)
        self.load_btn.setEnabled(False)
        buttons_layout.addWidget(self.load_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_project)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton { color: red; }")
        buttons_layout.addWidget(self.delete_btn)

        left_layout.addLayout(buttons_layout)

        # Right side - Project details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Project info header
        info_header = QLabel("Project Details")
        info_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_layout.addWidget(info_header)

        # Project details group
        details_group = QGroupBox("Selected Project")
        details_layout = QFormLayout(details_group)

        self.name_label = QLabel("No project selected")
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        details_layout.addRow("Name:", self.name_label)

        self.audio_label = QLabel("-")
        details_layout.addRow("Audio Files:", self.audio_label)

        self.cslp_label = QLabel("-")
        details_layout.addRow("CSLP File:", self.cslp_label)

        self.created_label = QLabel("-")
        details_layout.addRow("Created:", self.created_label)

        self.modified_label = QLabel("-")
        details_layout.addRow("Modified:", self.modified_label)

        right_layout.addWidget(details_group)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout(actions_group)

        self.save_current_btn = QPushButton("Save Current Project")
        self.save_current_btn.clicked.connect(self.save_current_project)
        self.save_current_btn.setEnabled(False)
        actions_layout.addWidget(self.save_current_btn)

        right_layout.addWidget(actions_group)

        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([350, 350])

        layout.addWidget(splitter)

        # Bottom buttons
        bottom_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_projects)
        bottom_layout.addWidget(self.refresh_btn)

        bottom_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.close_btn)

        layout.addLayout(bottom_layout)

    def load_projects(self):
        """Load and display available projects."""
        self.projects_list.clear()
        projects = self.project_manager.list_projects()

        if not projects:
            item = QListWidgetItem("No projects found")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.projects_list.addItem(item)
            return

        for project in projects:
            item = QListWidgetItem(project["name"])
            item.setData(Qt.ItemDataRole.UserRole, project)

            # Add some info in the text
            audio_count = len(project.get("audio_files", []))
            cslp_file = project.get("cslp_file", "None")
            modified = project.get("last_modified", "").split("T")[0] if project.get("last_modified") else ""

            item.setToolTip(f"Audio files: {audio_count}\nCSLP: {cslp_file}\nModified: {modified}")

            self.projects_list.addItem(item)

    def on_project_selected(self):
        """Handle project selection."""
        current_item = self.projects_list.currentItem()
        if not current_item or not current_item.data(Qt.ItemDataRole.UserRole):
            self.selected_project = None
            self.update_project_details(None)
            self.load_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        self.selected_project = current_item.data(Qt.ItemDataRole.UserRole)
        self.update_project_details(self.selected_project)
        self.load_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def on_project_double_clicked(self, item):
        """Handle double-click on project."""
        if item.data(Qt.ItemDataRole.UserRole):
            self.selected_project = item.data(Qt.ItemDataRole.UserRole)
            self.load_selected_project()

    def update_project_details(self, project: Optional[Dict[str, Any]]):
        """Update the project details display."""
        if not project:
            self.name_label.setText("No project selected")
            self.audio_label.setText("-")
            self.cslp_label.setText("-")
            self.created_label.setText("-")
            self.modified_label.setText("-")
            self.save_current_btn.setEnabled(False)
            return

        self.name_label.setText(project.get("name", "Unknown"))

        audio_files = project.get("audio_files", [])
        if audio_files:
            self.audio_label.setText(f"{len(audio_files)} file(s)")
            self.audio_label.setToolTip("\n".join(audio_files))
        else:
            self.audio_label.setText("None")

        cslp_file = project.get("cslp_file")
        self.cslp_label.setText(cslp_file or "None")

        created = project.get("created", "")
        if created:
            self.created_label.setText(created.split("T")[0])
        else:
            self.created_label.setText("-")

        modified = project.get("last_modified", "")
        if modified:
            self.modified_label.setText(modified.split("T")[0])
        else:
            self.modified_label.setText("-")

        # Enable save button if this is the current project
        current_project = self.project_manager.get_current_project_info()
        is_current_project = bool(current_project and 
                                current_project.get("id") and 
                                project.get("id") and 
                                current_project.get("id") == project.get("id"))
        self.save_current_btn.setEnabled(is_current_project)

    def create_new_project(self):
        """Create a new project."""
        name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
        if not ok or not name.strip():
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
            return

        # Check if project already exists
        existing_projects = self.project_manager.list_projects()
        if any(p["name"].lower() == name.lower() for p in existing_projects):
            result = QMessageBox.question(
                self, "Project Exists",
                f"A project named '{name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        # Create new project
        project = self.project_manager.create_project(name)
        if self.project_manager.save_project(project):
            QMessageBox.information(self, "Success", f"Project '{name}' created successfully!")
            self.load_projects()
        else:
            QMessageBox.critical(self, "Error", "Failed to create project.")

    def load_selected_project(self):
        """Load the selected project."""
        if not self.selected_project:
            return

        # Emit the project data
        self.project_selected.emit(self.selected_project)
        self.accept()  # Close dialog

    def delete_selected_project(self):
        """Delete the selected project."""
        if not self.selected_project:
            return

        result = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete project '{self.selected_project['name']}'?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            if self.project_manager.delete_project(self.selected_project["name"]):
                QMessageBox.information(self, "Success", "Project deleted successfully!")
                self.load_projects()
                self.selected_project = None
                self.update_project_details(None)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete project.")

    def save_current_project(self):
        """Save the current project."""
        current_project = self.project_manager.get_current_project_info()
        if current_project and self.project_manager.save_project(current_project):
            QMessageBox.information(self, "Success", "Project saved successfully!")
            self.load_projects()  # Refresh the list
        else:
            QMessageBox.critical(self, "Error", "Failed to save project.")