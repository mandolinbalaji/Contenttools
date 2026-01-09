"""
make_adhi_tala.py
Creates an Adhi Tala (8-beat) visual+audio video at a chosen BPM.
Two modes:
 - --use-ai: uses Replicate (Stability SDXL by default) to generate hand images
 - otherwise: creates simple labeled placeholder images

Usage examples:
 python make_adhi_tala.py --bpm 90 --cycles 4 --use-ai
 python make_adhi_tala.py --bpm 60 --cycles 6
"""
import os
import argparse
from pathlib import Path
import time

# Image and video libs
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import ImageClip, concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip

# Optional imports for AI
try:
    import replicate
    import requests
except Exception:
    replicate = None

# -------- CONFIG / PROMPTS (tweak these prompts to change look) ------
AI_MODEL = "stability-ai/sdxl"  # replicate model slug (default)
GEN_W, GEN_H = 512, 512

PROMPTS = {
    "clap": "photorealistic isolated human right hand performing a gentle clap, palm visible, high detail, isolated on white background, PNG",
    "little": "photorealistic isolated human right hand touching little finger (gesture), high detail, isolated on white background, PNG",
    "ring": "photorealistic isolated human right hand with ring-finger gesture, high detail, isolated on white background, PNG",
    "wave": "photorealistic isolated human right hand doing a gentle open-palm wave, high detail, isolated on white background, PNG",
}

# Adhi tala mapping (beats 1..8) -> gesture keys
BEAT_GESTURES = ["clap", "little", "ring", "wave", "wave", "clap", "wave", "clap"]
# (You can change that mapping if you want different kriya representation)


# ---------------- utility: placeholder image generator ----------------
def make_placeholder_images(outdir, size=(GEN_W, GEN_H)):
    outdir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    for name in PROMPTS.keys():
        img = Image.new("RGBA", size, (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        txt = name.upper()
        w, h = draw.textsize(txt, font=font)
        draw.ellipse((size[0]//4, size[1]//8, size[0]*3//4, size[1]*3//4), outline=(60,60,60), width=6)
        draw.text(((size[0]-w)//2, (size[1]-h)//2), txt, fill=(20,20,20), font=font)
        img.save(outdir / f"{name}.png")
    print(f"Placeholder images written to {outdir}")


# ---------------- AI image generation via Replicate ----------------
def generate_ai_images(outdir, api_token, model=AI_MODEL, width=GEN_W, height=GEN_H, wait=2.0):
    if replicate is None:
        raise RuntimeError("Replicate python package not installed. pip install replicate")
    outdir.mkdir(parents=True, exist_ok=True)
    # Ensure token available to replicate client
    os.environ.setdefault("REPLICATE_API_TOKEN", api_token)
    print("Using Replicate model:", model)
    for name, prompt in PROMPTS.items():
        print(f"Generating [{name}] ...")
        try:
            outputs = replicate.run(model, input={"prompt": prompt, "width": width, "height": height})
        except Exception as e:
            print("Replicate generation failed:", e)
            raise
        # outputs may be a list of FileOutput(s) or a single FileOutput
        # handle both
        filedata = None
        if isinstance(outputs, (list, tuple)):
            fileobj = outputs[0]
            filedata = fileobj.read()
        else:
            filedata = outputs.read()
        out_path = outdir / f"{name}.png"
        with open(out_path, "wb") as f:
            f.write(filedata)
        print("Saved ->", out_path)
        time.sleep(wait)  # polite pause


# ---------------- audio generator (moviepy AudioClip make_frame) -------
def build_click_audio_clip(beat_times, duration, fps=44100, click_dur=0.06, freq=1500.0):
    """
    Creates an AudioClip with short sine clicks at beat_times (list of seconds).
    """
    beat_times = np.array(sorted(beat_times))

    def make_frame(t):
        # t can be scalar or numpy array
        scalar = np.isscalar(t)
        ts = np.array([t]) if scalar else np.asarray(t)
        out = np.zeros_like(ts, dtype=float)
        for bt in beat_times:
            dt = ts - bt
            mask = (dt >= 0) & (dt < click_dur)
            if not mask.any():
                continue
            vals = np.sin(2 * np.pi * freq * dt[mask]) * (1 - (dt[mask] / click_dur))
            out[mask] += vals
        # normalize amplitude to avoid clipping
        maxamp = max(1.0, np.max(np.abs(out)) + 1e-9)
        out = out / (maxamp * 1.2)
        return float(out[0]) if scalar else out

    return AudioClip(make_frame, duration=duration, fps=fps)


# ---------------- assemble video ----------------
def assemble_video(images_dir, bpm, cycles, out_file="adhi_tala.mp4", fps=24):
    beat_sec = 60.0 / float(bpm)
    print(f"BPM {bpm} -> {beat_sec:.4f} sec per beat")
    # build list of ImageClips per beat, repeated for cycles
    clips = []
    beat_sequence = BEAT_GESTURES * cycles
    for idx, g in enumerate(beat_sequence):
        img_path = images_dir / f"{g}.png"
        if not img_path.exists():
            raise FileNotFoundError(f"Missing image for gesture '{g}': {img_path}")
        clip = ImageClip(str(img_path)).set_duration(beat_sec)
        clips.append(clip)
    video = concatenate_videoclips(clips, method="compose")
    total_duration = video.duration
    # beat_times (absolute)
    beat_times = [i * beat_sec for i in range(len(beat_sequence))]
    audio = build_click_audio_clip(beat_times, duration=total_duration)
    final = video.set_audio(audio)
    print("Exporting video (this may take a bit)...")
    final.write_videofile(out_file, fps=fps, codec="libx264", audio_codec="aac")
    print("Saved video to", out_file)


# ---------------------- main CLI -------------------------
def main():
    p = argparse.ArgumentPar
