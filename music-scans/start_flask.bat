@echo off
REM Set UTF-8 encoding to handle Unicode characters in lesson notes
chcp 65001 > nul

REM Navigate to the correct directory
cd /d "G:\My Drive\ContentTools\music-scans"

REM Run the Flask server
python3 app.py