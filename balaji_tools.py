#!/usr/bin/env python3
"""
Balaji's Tools - Music Production Dashboard
A unified interface for music production tools.

Features:
- Launch Precision Audio Player
- Start/Stop YouTube to MP3 Server
- Launch Ultimate Vocal Remover (UVR)
- Start SongIndex Server
"""

import sys
import subprocess
import os
from pathlib import Path
import threading
import time
import tempfile
import atexit

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QGroupBox, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon, QPixmap

def check_single_instance(force=False):
    """Check if another instance is already running and prevent multiple instances."""
    lock_file = Path(tempfile.gettempdir()) / 'balaji_tools_dashboard.lock'

    if lock_file.exists() and not force:
        try:
            # Try to read the PID from the lock file
            with open(lock_file, 'r') as f:
                pid_str = f.read().strip()

            if pid_str.isdigit():
                pid = int(pid_str)
                # Check if process is actually running
                try:
                    import psutil
                    if psutil.pid_exists(pid):
                        # Double check by looking for python process with our script name
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            if proc.info['pid'] == pid:
                                cmdline = proc.info.get('cmdline', [])
                                if any('balaji_tools.py' in str(arg) for arg in cmdline):
                                    return False  # Another instance is running
                except ImportError:
                    # psutil not available, fall back to simple check
                    return False
                except Exception:
                    pass  # Process check failed, assume not running

            # If we get here, the lock file exists but process isn't running
            # Clean up stale lock file
            lock_file.unlink()

        except (FileNotFoundError, ValueError, OSError):
            # Lock file corrupted or inaccessible, clean it up
            try:
                lock_file.unlink()
            except Exception:
                pass

    # Create lock file with current PID
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False

def cleanup_lock_file():
    """Clean up the lock file when the application exits."""
    lock_file = Path(tempfile.gettempdir()) / 'balaji_tools_dashboard.lock'
    try:
        if lock_file.exists():
            lock_file.unlink()
    except Exception:
        pass

class ToolLauncher(QObject):
    """Manages launching and monitoring external tools."""

    status_updated = pyqtSignal(str, str)  # tool_name, status

    def __init__(self):
        super().__init__()
        self.processes = {}
        self.uvr_path = r"C:\Users\mando\AppData\Local\Programs\Ultimate Vocal Remover\UVR_Launcher.exe"
        self.songindex_path = r"G:\My Drive\Music_Scans\app.py"

    def launch_precision_player(self):
        """Launch the precision audio player."""
        try:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent
            player_path = script_dir / 'precision_player.py'

            if not player_path.exists():
                self.status_updated.emit('precision_player', f'Error: precision_player.py not found at {player_path}')
                return False

            # Launch GUI application (don't use CREATE_NO_WINDOW for GUI apps)
            process = subprocess.Popen([sys.executable, str(player_path)],
                                     cwd=str(script_dir))
            self.processes['precision_player'] = process
            self.status_updated.emit('precision_player', 'Running')
            return True
        except Exception as e:
            self.status_updated.emit('precision_player', f'Error: {str(e)}')
            return False

    def launch_uvr(self):
        """Launch Ultimate Vocal Remover."""
        try:
            if not Path(self.uvr_path).exists():
                self.status_updated.emit('uvr', 'Error: UVR not found at specified path')
                return False

            process = subprocess.Popen([self.uvr_path],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            self.processes['uvr'] = process
            self.status_updated.emit('uvr', 'Running')
            return True
        except Exception as e:
            self.status_updated.emit('uvr', f'Error: {str(e)}')
            return False

    def start_youtube_server(self):
        """Start the YouTube to MP3 server."""
        try:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent
            server_path = script_dir / 'youtube_to_mp3_server.py'

            if not server_path.exists():
                self.status_updated.emit('youtube_server', f'Error: youtube_to_mp3_server.py not found at {server_path}')
                return False

            process = subprocess.Popen([sys.executable, str(server_path)],
                                     cwd=str(script_dir),
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            self.processes['youtube_server'] = process
            self.status_updated.emit('youtube_server', 'Running (port 7773)')
            return True
        except Exception as e:
            self.status_updated.emit('youtube_server', f'Error: {str(e)}')
            return False

    def stop_youtube_server(self):
        """Stop all YouTube servers on port 7773."""
        try:
            # Kill any processes on port 7773
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                pids_to_kill = set()

                for line in lines:
                    if ':7773' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1].strip()
                            if pid.isdigit():
                                pids_to_kill.add(pid)

                # Kill each process
                killed_count = 0
                for pid in pids_to_kill:
                    try:
                        subprocess.run(
                            ['taskkill', '/PID', pid, '/F'],
                            capture_output=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        killed_count += 1
                    except Exception:
                        pass

                if killed_count > 0:
                    self.status_updated.emit('youtube_server', f'Stopped ({killed_count} processes killed)')
                else:
                    self.status_updated.emit('youtube_server', 'No servers found running')
            else:
                self.status_updated.emit('youtube_server', 'Error checking port status')

        except Exception as e:
            self.status_updated.emit('youtube_server', f'Error stopping: {str(e)}')

        # Remove from tracked processes
        if 'youtube_server' in self.processes:
            del self.processes['youtube_server']

    def launch_songindex_server(self):
        """Launch the SongIndex server."""
        try:
            if not Path(self.songindex_path).exists():
                self.status_updated.emit('songindex', 'Error: SongIndex app.py not found')
                return False

            process = subprocess.Popen([sys.executable, self.songindex_path],
                                     cwd=str(Path(self.songindex_path).parent),
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            self.processes['songindex'] = process
            self.status_updated.emit('songindex', 'Running')
            return True
        except Exception as e:
            self.status_updated.emit('songindex', f'Error: {str(e)}')
            return False

    def stop_songindex_server(self):
        """Stop all SongIndex servers on port 5000."""
        try:
            # Kill any processes on port 5000
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                pids_to_kill = set()

                for line in lines:
                    if ':5000' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1].strip()
                            if pid.isdigit():
                                pids_to_kill.add(pid)

                # Kill each process
                killed_count = 0
                for pid in pids_to_kill:
                    try:
                        subprocess.run(
                            ['taskkill', '/PID', pid, '/F'],
                            capture_output=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        killed_count += 1
                    except Exception:
                        pass

                if killed_count > 0:
                    self.status_updated.emit('songindex', f'Stopped ({killed_count} processes killed)')
                else:
                    self.status_updated.emit('songindex', 'No servers found running')
            else:
                self.status_updated.emit('songindex', 'Error checking port status')

        except Exception as e:
            self.status_updated.emit('songindex', f'Error stopping: {str(e)}')

        # Remove from tracked processes
        if 'songindex' in self.processes:
            del self.processes['songindex']

    def launch_format_converter(self):
        """Launch the AnytuneToLRC format converter (opens index.html in browser)."""
        try:
            import webbrowser
            # Get the directory where this script is located
            script_dir = Path(__file__).parent
            index_path = script_dir / 'index.html'

            if not index_path.exists():
                self.status_updated.emit('format_converter', f'Error: index.html not found at {index_path}')
                return False

            webbrowser.open(f'file://{index_path}')
            self.status_updated.emit('format_converter', 'Opened in browser')
            return True
        except Exception as e:
            self.status_updated.emit('format_converter', f'Error: {str(e)}')
            return False

    def launch_generate_video(self):
        """Launch the generate video tool."""
        try:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent
            video_path = script_dir / 'generate_video.py'

            if not video_path.exists():
                self.status_updated.emit('generate_video', f'Error: generate_video.py not found at {video_path}')
                return False

            process = subprocess.Popen([sys.executable, str(video_path)],
                                     cwd=str(script_dir),
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            self.processes['generate_video'] = process
            self.status_updated.emit('generate_video', 'Running')
            return True
        except Exception as e:
            self.status_updated.emit('generate_video', f'Error: {str(e)}')
            return False

    def launch_pdf_extractor(self):
        """Launch the PDF/Image extractor tool."""
        try:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent
            extractor_path = script_dir / 'pdf_image_extractor.py'

            if not extractor_path.exists():
                self.status_updated.emit('pdf_extractor', f'Error: pdf_image_extractor.py not found at {extractor_path}')
                return False

            # Launch GUI application (don't use CREATE_NO_WINDOW for GUI apps)
            process = subprocess.Popen([sys.executable, str(extractor_path)],
                                     cwd=str(script_dir))
            self.processes['pdf_extractor'] = process
            self.status_updated.emit('pdf_extractor', 'Running')
            return True
        except Exception as e:
            self.status_updated.emit('pdf_extractor', f'Error: {str(e)}')
            return False

    def check_process_status(self):
        """Check status of all running processes."""
        for name, process in list(self.processes.items()):
            if process.poll() is not None:
                # Process has ended
                del self.processes[name]
                if name == 'youtube_server':
                    self.status_updated.emit(name, 'Stopped')
                elif name == 'songindex':
                    self.status_updated.emit(name, 'Stopped')
                else:
                    self.status_updated.emit(name, 'Closed')

    def stop_all_processes(self):
        """Stop all running processes."""
        for process_name, process in list(self.processes.items()):
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    # Wait a bit for graceful termination
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        process.kill()
                        process.wait(timeout=2)
            except Exception as e:
                print(f"Error terminating {process_name}: {e}")
            finally:
                # Remove from tracking regardless of termination success
                if process_name in self.processes:
                    del self.processes[process_name]


class BalajiTools(QMainWindow):
    """Main dashboard window."""

    def __init__(self):
        super().__init__()
        self.launcher = ToolLauncher()
        self.launcher.status_updated.connect(self.on_status_update)

        self.status_labels = {}
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Balaji's Tools - Music Production Dashboard")
        self.setMinimumSize(900, 700)
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
                padding: 15px 25px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
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
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎵 Balaji's Music Production Tools")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ecf0f1; margin-bottom: 10px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Create splitter for tools and log
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Tools section
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setSpacing(15)

        # Audio Tools
        audio_group = QGroupBox("🎼 Audio Production")
        audio_layout = QGridLayout(audio_group)
        audio_layout.setSpacing(10)
        audio_layout.setContentsMargins(10, 10, 10, 10)

        # Precision Player
        player_btn = QPushButton("🎵\nPrecision\nPlayer")
        player_btn.clicked.connect(self.launch_precision_player)
        player_btn.setMinimumSize(100, 100)
        player_btn.setMaximumSize(120, 120)
        player_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                text-align: center;
                padding: 5px;
            }
        """)
        audio_layout.addWidget(player_btn, 0, 0, Qt.AlignmentFlag.AlignCenter)

        self.status_labels['precision_player'] = QLabel("Not running")
        self.status_labels['precision_player'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['precision_player'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(self.status_labels['precision_player'], 1, 0, Qt.AlignmentFlag.AlignCenter)

        # UVR
        uvr_btn = QPushButton("🎤\nUVR\nRemover")
        uvr_btn.clicked.connect(self.launch_uvr)
        uvr_btn.setMinimumSize(100, 100)
        uvr_btn.setMaximumSize(120, 120)
        uvr_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                text-align: center;
                padding: 5px;
            }
        """)
        audio_layout.addWidget(uvr_btn, 0, 1, Qt.AlignmentFlag.AlignCenter)

        self.status_labels['uvr'] = QLabel("Not running")
        self.status_labels['uvr'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['uvr'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(self.status_labels['uvr'], 1, 1, Qt.AlignmentFlag.AlignCenter)

        # Format Converter
        format_btn = QPushButton("🔄\nFormat\nConverter")
        format_btn.clicked.connect(self.launch_format_converter)
        format_btn.setMinimumSize(100, 100)
        format_btn.setMaximumSize(120, 120)
        format_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                text-align: center;
                padding: 5px;
            }
        """)
        audio_layout.addWidget(format_btn, 0, 2, Qt.AlignmentFlag.AlignCenter)

        self.status_labels['format_converter'] = QLabel("Ready")
        self.status_labels['format_converter'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['format_converter'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(self.status_labels['format_converter'], 1, 2, Qt.AlignmentFlag.AlignCenter)

        # Generate Video
        video_btn = QPushButton("🎬\nGenerate\nVideo")
        video_btn.clicked.connect(self.launch_generate_video)
        video_btn.setMinimumSize(100, 100)
        video_btn.setMaximumSize(120, 120)
        video_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                text-align: center;
                padding: 5px;
            }
        """)
        audio_layout.addWidget(video_btn, 0, 3, Qt.AlignmentFlag.AlignCenter)

        self.status_labels['generate_video'] = QLabel("Not running")
        self.status_labels['generate_video'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['generate_video'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(self.status_labels['generate_video'], 1, 3, Qt.AlignmentFlag.AlignCenter)

        # PDF/Image Extractor
        pdf_btn = QPushButton("📄\nPDF/Image\nExtractor")
        pdf_btn.clicked.connect(self.launch_pdf_extractor)
        pdf_btn.setMinimumSize(100, 100)
        pdf_btn.setMaximumSize(120, 120)
        pdf_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                text-align: center;
                padding: 5px;
            }
        """)
        audio_layout.addWidget(pdf_btn, 2, 0, Qt.AlignmentFlag.AlignCenter)

        self.status_labels['pdf_extractor'] = QLabel("Not running")
        self.status_labels['pdf_extractor'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['pdf_extractor'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(self.status_labels['pdf_extractor'], 3, 0, Qt.AlignmentFlag.AlignCenter)

        tools_layout.addWidget(audio_group)

        # Server Tools
        server_group = QGroupBox("🌐 Server Tools")
        server_layout = QGridLayout(server_group)
        server_layout.setSpacing(10)
        server_layout.setContentsMargins(10, 10, 10, 10)

        # YouTube Server
        youtube_widget = QWidget()
        youtube_layout = QVBoxLayout(youtube_widget)
        youtube_layout.setSpacing(5)

        self.youtube_start_btn = QPushButton("▶\nStart\nYouTube")
        self.youtube_start_btn.clicked.connect(self.start_youtube_server)
        self.youtube_start_btn.setMinimumSize(80, 80)
        self.youtube_start_btn.setMaximumSize(100, 100)
        self.youtube_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-size: 10px;
                text-align: center;
                padding: 2px;
            }
            QPushButton:hover { background-color: #229954; }
        """)

        self.youtube_stop_btn = QPushButton("⏹\nStop\nYouTube")
        self.youtube_stop_btn.clicked.connect(self.stop_youtube_server)
        self.youtube_stop_btn.setEnabled(False)
        self.youtube_stop_btn.setMinimumSize(80, 80)
        self.youtube_stop_btn.setMaximumSize(100, 100)
        self.youtube_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 10px;
                text-align: center;
                padding: 2px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)

        youtube_layout.addWidget(self.youtube_start_btn)
        youtube_layout.addWidget(self.youtube_stop_btn)

        self.status_labels['youtube_server'] = QLabel("Stopped")
        self.status_labels['youtube_server'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['youtube_server'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        youtube_layout.addWidget(self.status_labels['youtube_server'])

        server_layout.addWidget(youtube_widget, 0, 0, Qt.AlignmentFlag.AlignCenter)

        # SongIndex Server
        songindex_widget = QWidget()
        songindex_layout = QVBoxLayout(songindex_widget)
        songindex_layout.setSpacing(5)

        songindex_btn = QPushButton("📚\nLaunch\nSongIndex")
        songindex_btn.clicked.connect(self.launch_songindex_server)
        songindex_btn.setMinimumSize(80, 80)
        songindex_btn.setMaximumSize(100, 100)
        songindex_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                text-align: center;
                padding: 2px;
            }
        """)

        self.songindex_stop_btn = QPushButton("⏹\nStop\nSongIndex")
        self.songindex_stop_btn.clicked.connect(self.stop_songindex_server)
        self.songindex_stop_btn.setEnabled(False)
        self.songindex_stop_btn.setMinimumSize(80, 80)
        self.songindex_stop_btn.setMaximumSize(100, 100)
        self.songindex_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 10px;
                text-align: center;
                padding: 2px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)

        songindex_layout.addWidget(songindex_btn)
        songindex_layout.addWidget(self.songindex_stop_btn)

        self.status_labels['songindex'] = QLabel("Not running")
        self.status_labels['songindex'].setStyleSheet("color: #95a5a6; font-size: 10px; text-align: center;")
        self.status_labels['songindex'].setAlignment(Qt.AlignmentFlag.AlignCenter)
        songindex_layout.addWidget(self.status_labels['songindex'])

        server_layout.addWidget(songindex_widget, 0, 1, Qt.AlignmentFlag.AlignCenter)

        tools_layout.addWidget(server_group)
        tools_layout.addStretch()

        # Log section
        log_group = QGroupBox("📋 Activity Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        self.log_text.append("Welcome to Balaji's Tools Dashboard!\n")
        self.log_text.append("Click buttons above to launch tools.\n")
        log_layout.addWidget(self.log_text)

        # Add to splitter
        splitter.addWidget(tools_widget)
        splitter.addWidget(log_group)
        splitter.setSizes([500, 200])

        layout.addWidget(splitter)

    def setup_timer(self):
        """Setup timer to check process status."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.launcher.check_process_status)
        self.timer.start(2000)  # Check every 2 seconds

    def launch_precision_player(self):
        """Launch the precision player."""
        if self.launcher.launch_precision_player():
            self.log_text.append("🎵 Launched Precision Audio Player")
        else:
            self.log_text.append("❌ Failed to launch Precision Audio Player")

    def launch_uvr(self):
        """Launch UVR."""
        if self.launcher.launch_uvr():
            self.log_text.append("🎤 Launched Ultimate Vocal Remover")
        else:
            self.log_text.append("❌ Failed to launch UVR")

    def start_youtube_server(self):
        """Start YouTube server."""
        if self.launcher.start_youtube_server():
            self.youtube_start_btn.setEnabled(False)
            self.youtube_stop_btn.setEnabled(True)
            self.log_text.append("🌐 Started YouTube to MP3 Server (port 7773)")
        else:
            self.log_text.append("❌ Failed to start YouTube Server")

    def stop_youtube_server(self):
        """Stop YouTube server."""
        self.launcher.stop_youtube_server()
        self.youtube_start_btn.setEnabled(True)
        self.youtube_stop_btn.setEnabled(False)
        self.log_text.append("🛑 Stopped YouTube Server")

    def launch_songindex_server(self):
        """Launch SongIndex server."""
        if self.launcher.launch_songindex_server():
            self.songindex_stop_btn.setEnabled(True)
            self.log_text.append("📚 Launched SongIndex Server")
        else:
            self.log_text.append("❌ Failed to launch SongIndex Server")

    def stop_songindex_server(self):
        """Stop SongIndex server."""
        self.launcher.stop_songindex_server()
        self.songindex_stop_btn.setEnabled(False)
        self.log_text.append("🛑 Stopped SongIndex Server")

    def launch_format_converter(self):
        """Launch the format converter."""
        if self.launcher.launch_format_converter():
            self.log_text.append("🔄 Opened AnytuneToLRC Format Converter")
        else:
            self.log_text.append("❌ Failed to open Format Converter")

    def launch_generate_video(self):
        """Launch the generate video tool."""
        if self.launcher.launch_generate_video():
            self.log_text.append("🎬 Launched Generate Video Tool")
        else:
            self.log_text.append("❌ Failed to launch Generate Video Tool")

    def launch_pdf_extractor(self):
        """Launch the PDF/Image extractor."""
        if self.launcher.launch_pdf_extractor():
            self.log_text.append("📄 Launched PDF/Image Extractor")
        else:
            self.log_text.append("❌ Failed to launch PDF/Image Extractor")

    def on_status_update(self, tool_name, status):
        """Handle status updates from tools."""
        if tool_name in self.status_labels:
            self.status_labels[tool_name].setText(status)

            # Update button states for YouTube server
            if tool_name == 'youtube_server':
                if 'Running' in status:
                    self.youtube_start_btn.setEnabled(False)
                    self.youtube_stop_btn.setEnabled(True)
                else:
                    self.youtube_start_btn.setEnabled(True)
                    self.youtube_stop_btn.setEnabled(False)

            # Update button states for SongIndex server
            elif tool_name == 'songindex':
                if 'Running' in status:
                    self.songindex_stop_btn.setEnabled(True)
                else:
                    self.songindex_stop_btn.setEnabled(False)

    def closeEvent(self, event):
        """Clean up on close - stop all running processes."""
        # Stop all running processes
        self.launcher.stop_all_processes()

        # Stop servers using their specific stop methods (for port cleanup)
        self.launcher.stop_youtube_server()
        self.launcher.stop_songindex_server()

        cleanup_lock_file()  # Clean up lock file
        event.accept()


def main():
    # Check command line arguments for force start
    force_start = '--force' in sys.argv or '-f' in sys.argv

    # Check for single instance
    if not check_single_instance(force=force_start):
        # Show error message using a simple dialog
        app = QApplication(sys.argv)
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Already Running")
        msg.setText("Balaji's Tools dashboard is already running.")
        msg.setInformativeText("Only one instance is allowed.\n\nUse --force or -f to start anyway.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        cleanup_lock_file()  # Clean up in case of error
        sys.exit(1)

    # Register cleanup function
    atexit.register(cleanup_lock_file)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = BalajiTools()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()