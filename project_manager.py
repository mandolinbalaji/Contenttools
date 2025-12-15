#!/usr/bin/env python3
"""
Project Manager for Precision Player
Handles saving/loading project configurations with audio files and CSLP data.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid

class ProjectManager:
    """Manages project configurations for the precision player."""

    def __init__(self, projects_dir: str = "projects"):
        """Initialize project manager with projects directory."""
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(exist_ok=True)
        self.current_project: Optional[Dict[str, Any]] = None
        self.current_project_path: Optional[Path] = None
        self.auto_save_enabled = False

    def create_project(self, name: str, audio_files: List[str] = None, cslp_file: str = None) -> Dict[str, Any]:
        """Create a new project configuration."""
        project = {
            "id": str(uuid.uuid4()),
            "name": name,
            "audio_files": audio_files or [],
            "cslp_file": cslp_file,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "version": "1.0"
        }
        return project

    def save_project(self, project: Dict[str, Any]) -> bool:
        """Save project to JSON file."""
        try:
            project["last_modified"] = datetime.now().isoformat()
            project_path = self.projects_dir / f"{project['name'].replace(' ', '_')}.json"

            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(project, f, indent=2, ensure_ascii=False)

            self.current_project = project
            self.current_project_path = project_path
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def load_project(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """Load project from JSON file."""
        try:
            with open(project_path, 'r', encoding='utf-8') as f:
                project = json.load(f)

            # Validate project structure
            required_fields = ["id", "name", "audio_files", "cslp_file"]
            if not all(field in project for field in required_fields):
                print(f"Invalid project file: missing required fields")
                return None

            self.current_project = project
            self.current_project_path = project_path
            return project
        except Exception as e:
            print(f"Error loading project: {e}")
            return None

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all available projects."""
        projects = []
        for json_file in self.projects_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    project = json.load(f)
                project["_file_path"] = str(json_file)
                projects.append(project)
            except Exception as e:
                print(f"Error reading project file {json_file}: {e}")

        # Sort by last modified date
        projects.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
        return projects

    def update_project_audio(self, audio_files: List[str]) -> bool:
        """Update audio files in current project."""
        if not self.current_project:
            return False

        self.current_project["audio_files"] = audio_files
        if self.auto_save_enabled:
            return self.save_project(self.current_project)
        return True

    def update_project_cslp(self, cslp_file: str) -> bool:
        """Update CSLP file in current project."""
        if not self.current_project:
            return False

        self.current_project["cslp_file"] = cslp_file
        if self.auto_save_enabled:
            return self.save_project(self.current_project)
        return True

    def enable_auto_save(self):
        """Enable automatic saving of project changes."""
        self.auto_save_enabled = True

    def disable_auto_save(self):
        """Disable automatic saving of project changes."""
        self.auto_save_enabled = False

    def get_current_project_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current project."""
        return self.current_project

    def close_project(self) -> bool:
        """Close current project, saving if auto-save is enabled."""
        if self.current_project and self.auto_save_enabled:
            success = self.save_project(self.current_project)
            if success:
                print(f"Auto-saved project: {self.current_project['name']}")

        self.current_project = None
        self.current_project_path = None
        self.auto_save_enabled = False
        return True

    def delete_project(self, project_name: str) -> bool:
        """Delete a project file."""
        try:
            project_path = self.projects_dir / f"{project_name.replace(' ', '_')}.json"
            if project_path.exists():
                project_path.unlink()
                return True
        except Exception as e:
            print(f"Error deleting project: {e}")
        return False