#!/usr/bin/env python3
"""
Launcher for Balaji's Tools Dashboard
Run this to start the main music production dashboard.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Launch the dashboard."""
    print("🎵 Starting Balaji's Tools - Music Production Dashboard...")
    print("Loading tools...")

    try:
        from balaji_tools import main as dashboard_main
        dashboard_main()
    except ImportError as e:
        print(f"❌ Error: Could not import dashboard: {e}")
        print("Make sure all required packages are installed:")
        print("pip install PyQt6 numpy sounddevice soundfile flask flask-cors yt-dlp")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()