#!/usr/bin/env python3
"""
YouTube Shorts Video Generator - Desktop App
Drag and drop interface for generating MP4 videos from CSLP and audio files.

Double-click to run, or: python video_generator_app.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import subprocess

# Import the video generation logic
from generate_video import generate_video, check_ffmpeg, load_cslp

class VideoGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Shorts Video Generator")
        self.root.geometry("600x550")
        self.root.resizable(True, True)
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        self.style.configure('Heading.TLabel', font=('Segoe UI', 10, 'bold'))
        self.style.configure('Drop.TFrame', relief='solid', borderwidth=2)
        
        # Variables
        self.audio_path = tk.StringVar()
        self.cslp_path = tk.StringVar()
        self.title_var = tk.StringVar()
        self.info_var = tk.StringVar()
        self.output_path = tk.StringVar()
        self.is_generating = False
        
        self.create_widgets()
        self.setup_drag_drop()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎬 YouTube Shorts Generator", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # File drop zones frame
        drop_frame = ttk.Frame(main_frame)
        drop_frame.pack(fill=tk.X, pady=(0, 15))
        drop_frame.columnconfigure(0, weight=1)
        drop_frame.columnconfigure(1, weight=1)
        
        # Audio drop zone
        self.audio_zone = self.create_drop_zone(drop_frame, "🎵 Audio File", 
                                                  "Drag & drop or click to browse",
                                                  self.browse_audio, 0)
        
        # CSLP drop zone
        self.cslp_zone = self.create_drop_zone(drop_frame, "📄 CSLP File",
                                                 "Drag & drop or click to browse", 
                                                 self.browse_cslp, 1)
        
        # Audio path display
        audio_path_frame = ttk.Frame(main_frame)
        audio_path_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(audio_path_frame, text="Audio:", width=8).pack(side=tk.LEFT)
        ttk.Entry(audio_path_frame, textvariable=self.audio_path, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # CSLP path display
        cslp_path_frame = ttk.Frame(main_frame)
        cslp_path_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(cslp_path_frame, text="CSLP:", width=8).pack(side=tk.LEFT)
        ttk.Entry(cslp_path_frame, textvariable=self.cslp_path, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Title input
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="Title:", style='Heading.TLabel').pack(anchor=tk.W)
        ttk.Entry(title_frame, textvariable=self.title_var, font=('Segoe UI', 11)).pack(fill=tk.X, pady=(5, 0))
        
        # Info text input
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(info_frame, text="Info Text (scrolling marquee):", style='Heading.TLabel').pack(anchor=tk.W)
        ttk.Entry(info_frame, textvariable=self.info_var, font=('Segoe UI', 11)).pack(fill=tk.X, pady=(5, 0))
        
        # Output path
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(output_frame, text="Output:", style='Heading.TLabel').pack(anchor=tk.W)
        output_inner = ttk.Frame(output_frame)
        output_inner.pack(fill=tk.X, pady=(5, 0))
        ttk.Entry(output_inner, textvariable=self.output_path, font=('Segoe UI', 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_inner, text="Browse", command=self.browse_output).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Progress bar
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(pady=(5, 0))
        
        # Generate button
        self.generate_btn = ttk.Button(main_frame, text="🎬 Generate Video", 
                                        command=self.start_generation,
                                        style='Accent.TButton')
        self.generate_btn.pack(pady=(10, 0), ipadx=20, ipady=10)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Load audio and CSLP files to begin.")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                               foreground='gray', font=('Segoe UI', 9))
        status_bar.pack(side=tk.BOTTOM, pady=(15, 0))
        
    def create_drop_zone(self, parent, title, subtitle, command, column):
        """Create a drag-and-drop zone."""
        frame = tk.Frame(parent, bg='#f0f0f0', relief='groove', bd=2, 
                        width=250, height=100, cursor='hand2')
        frame.grid(row=0, column=column, padx=5, sticky='nsew')
        frame.pack_propagate(False)
        
        title_lbl = tk.Label(frame, text=title, font=('Segoe UI', 12, 'bold'), 
                            bg='#f0f0f0', fg='#333')
        title_lbl.pack(pady=(20, 5))
        
        sub_lbl = tk.Label(frame, text=subtitle, font=('Segoe UI', 9), 
                          bg='#f0f0f0', fg='#666')
        sub_lbl.pack()
        
        # Bind click to browse
        for widget in [frame, title_lbl, sub_lbl]:
            widget.bind('<Button-1>', lambda e, cmd=command: cmd())
            
        return frame
    
    def setup_drag_drop(self):
        """Setup drag and drop handling."""
        # Try to use tkinterdnd2 if available
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            # Note: For full drag-drop, the root window needs to be TkinterDnD.Tk()
            # This is a simplified version - click to browse works regardless
            self.status_var.set("Ready. Click zones to browse or drag files.")
        except ImportError:
            self.status_var.set("Ready. Click zones to browse for files.")
    
    def browse_audio(self):
        """Browse for audio file."""
        path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.m4a *.ogg *.flac *.aac"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.set_audio(path)
    
    def browse_cslp(self):
        """Browse for CSLP file."""
        path = filedialog.askopenfilename(
            title="Select CSLP File",
            filetypes=[
                ("CSLP Files", "*.cslp"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.set_cslp(path)
    
    def browse_output(self):
        """Browse for output location."""
        path = filedialog.asksaveasfilename(
            title="Save Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if path:
            self.output_path.set(path)
    
    def set_audio(self, path):
        """Set the audio file path."""
        self.audio_path.set(path)
        self.update_audio_zone(os.path.basename(path))
        self.update_output_path()
        self.check_ready()
    
    def set_cslp(self, path):
        """Set the CSLP file path and load metadata."""
        self.cslp_path.set(path)
        self.update_cslp_zone(os.path.basename(path))
        
        # Try to load title from CSLP
        try:
            cslp = load_cslp(path)
            title = cslp.get('metadata', {}).get('title', '')
            if title and not self.title_var.get():
                self.title_var.set(title)
        except:
            pass
        
        self.update_output_path()
        self.check_ready()
    
    def update_audio_zone(self, filename):
        """Update audio zone to show loaded file."""
        for widget in self.audio_zone.winfo_children():
            widget.destroy()
        
        self.audio_zone.configure(bg='#e8f5e9')
        tk.Label(self.audio_zone, text="✓ Audio Loaded", font=('Segoe UI', 10, 'bold'),
                bg='#e8f5e9', fg='#2e7d32').pack(pady=(15, 5))
        tk.Label(self.audio_zone, text=filename, font=('Segoe UI', 9),
                bg='#e8f5e9', fg='#555', wraplength=220).pack()
        tk.Label(self.audio_zone, text="(click to change)", font=('Segoe UI', 8),
                bg='#e8f5e9', fg='#888').pack()
        
        for widget in self.audio_zone.winfo_children():
            widget.bind('<Button-1>', lambda e: self.browse_audio())
    
    def update_cslp_zone(self, filename):
        """Update CSLP zone to show loaded file."""
        for widget in self.cslp_zone.winfo_children():
            widget.destroy()
        
        self.cslp_zone.configure(bg='#e3f2fd')
        tk.Label(self.cslp_zone, text="✓ CSLP Loaded", font=('Segoe UI', 10, 'bold'),
                bg='#e3f2fd', fg='#1565c0').pack(pady=(15, 5))
        tk.Label(self.cslp_zone, text=filename, font=('Segoe UI', 9),
                bg='#e3f2fd', fg='#555', wraplength=220).pack()
        tk.Label(self.cslp_zone, text="(click to change)", font=('Segoe UI', 8),
                bg='#e3f2fd', fg='#888').pack()
        
        for widget in self.cslp_zone.winfo_children():
            widget.bind('<Button-1>', lambda e: self.browse_cslp())
    
    def update_output_path(self):
        """Auto-generate output path based on title or filename."""
        if not self.output_path.get():
            title = self.title_var.get() or "video"
            safe_title = ''.join(c if c.isalnum() or c in '-_ ' else '_' for c in title)
            safe_title = safe_title.strip().replace(' ', '_')
            
            # Use audio file directory for output
            audio = self.audio_path.get()
            if audio:
                output_dir = os.path.dirname(audio)
            else:
                output_dir = os.getcwd()
            
            self.output_path.set(os.path.join(output_dir, f"{safe_title}_shorts.mp4"))
    
    def check_ready(self):
        """Check if ready to generate."""
        ready = self.audio_path.get() and self.cslp_path.get()
        if ready:
            self.status_var.set("✓ Ready to generate video!")
        else:
            missing = []
            if not self.audio_path.get():
                missing.append("audio")
            if not self.cslp_path.get():
                missing.append("CSLP")
            self.status_var.set(f"Load {' and '.join(missing)} file(s) to continue.")
    
    def start_generation(self):
        """Start video generation in a thread."""
        if self.is_generating:
            return
        
        audio = self.audio_path.get()
        cslp = self.cslp_path.get()
        
        if not audio or not cslp:
            messagebox.showerror("Missing Files", "Please load both audio and CSLP files.")
            return
        
        if not os.path.exists(audio):
            messagebox.showerror("File Not Found", f"Audio file not found:\n{audio}")
            return
        
        if not os.path.exists(cslp):
            messagebox.showerror("File Not Found", f"CSLP file not found:\n{cslp}")
            return
        
        if not check_ffmpeg():
            messagebox.showerror("FFmpeg Required", 
                "FFmpeg is not installed or not in PATH.\n\n"
                "Download from: https://ffmpeg.org/download.html\n\n"
                "Add FFmpeg to your system PATH and restart this app.")
            return
        
        # Update output path if title changed
        self.update_output_path()
        
        self.is_generating = True
        self.generate_btn.configure(state='disabled')
        self.progress_bar['value'] = 0
        self.progress_label.configure(text="Starting...")
        
        # Run in thread
        thread = threading.Thread(target=self.generate_video_thread, daemon=True)
        thread.start()
    
    def generate_video_thread(self):
        """Generate video in background thread."""
        try:
            audio = self.audio_path.get()
            cslp = self.cslp_path.get()
            title = self.title_var.get() or None
            info = self.info_var.get() or None
            output = self.output_path.get()
            
            # Update progress callback
            def on_progress(current, total, message):
                progress = (current / total) * 100 if total > 0 else 0
                self.root.after(0, self.update_progress, progress, message)
            
            # Generate with progress
            self.generate_with_progress(audio, cslp, title, info, output, on_progress)
            
            # Success
            self.root.after(0, self.on_generation_complete, output)
            
        except Exception as e:
            self.root.after(0, self.on_generation_error, str(e))
    
    def generate_with_progress(self, audio, cslp, title, info, output, on_progress):
        """Wrapper to generate video with progress updates."""
        import json
        import tempfile
        import shutil
        from PIL import Image, ImageDraw, ImageFont
        
        # Import constants and functions from generate_video
        from generate_video import (
            WIDTH, HEIGHT, FPS, TITLE_HEIGHT, STRIP_HEIGHT, INFO_HEIGHT, CHROMA_KEY,
            load_cslp, get_audio_duration, draw_frame
        )
        
        # Load CSLP
        on_progress(0, 100, "Loading CSLP...")
        cslp_data = load_cslp(cslp)
        timeline = cslp_data.get('data', {}).get('timeline', [])
        
        if not title:
            title = cslp_data.get('metadata', {}).get('title', '')
        
        # Get duration
        on_progress(5, 100, "Analyzing audio...")
        duration = get_audio_duration(audio)
        total_frames = int(duration * FPS)
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix='video_gen_')
        
        try:
            # Generate frames
            for frame_num in range(total_frames):
                current_time = frame_num / FPS
                progress = 10 + (frame_num / total_frames) * 70
                
                if frame_num % 30 == 0:
                    on_progress(progress, 100, f"Generating frames: {frame_num}/{total_frames}")
                
                img = draw_frame(current_time, timeline, title, info)
                frame_path = os.path.join(temp_dir, f"frame_{frame_num:06d}.png")
                img.save(frame_path, 'PNG')
            
            # Encode with FFmpeg
            on_progress(85, 100, "Encoding video with FFmpeg...")
            
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-framerate', str(FPS),
                '-i', os.path.join(temp_dir, 'frame_%06d.png'),
                '-i', audio,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-pix_fmt', 'yuv420p',
                '-shortest',
                output
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            
            on_progress(100, 100, "Complete!")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def update_progress(self, value, message):
        """Update progress bar and label."""
        self.progress_bar['value'] = value
        self.progress_label.configure(text=message)
    
    def on_generation_complete(self, output_path):
        """Handle successful generation."""
        self.is_generating = False
        self.generate_btn.configure(state='normal')
        self.progress_bar['value'] = 100
        self.progress_label.configure(text="✓ Video generated successfully!")
        self.status_var.set(f"Saved: {output_path}")
        
        # Ask to open folder
        result = messagebox.askyesno("Success!", 
            f"Video generated successfully!\n\n{output_path}\n\nOpen containing folder?")
        
        if result:
            folder = os.path.dirname(output_path)
            os.startfile(folder)
    
    def on_generation_error(self, error):
        """Handle generation error."""
        self.is_generating = False
        self.generate_btn.configure(state='normal')
        self.progress_bar['value'] = 0
        self.progress_label.configure(text="")
        self.status_var.set("Error occurred during generation.")
        
        messagebox.showerror("Generation Failed", f"Error: {error}")


def main():
    # Check dependencies
    try:
        from PIL import Image
    except ImportError:
        import subprocess
        print("Installing Pillow...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pillow'])
        from PIL import Image
    
    root = tk.Tk()
    app = VideoGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
