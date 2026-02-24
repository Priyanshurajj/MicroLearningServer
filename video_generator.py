"""
video_generator.py - Video generation from slide data using MoviePy v2 + Pillow.

Creates a vertical (720×1280) MP4 video where each slide is rendered as
white text on a dark background with fade-in/out transitions and an audio track.

Requirements:
    - moviepy (v2.x), Pillow, numpy
    - FFmpeg must be installed and available on PATH
      Windows:  choco install ffmpeg   OR   download from https://ffmpeg.org/download.html
      Linux:    sudo apt install ffmpeg
      macOS:    brew install ffmpeg
"""

import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips,
)
from moviepy.video.fx import CrossFadeIn, CrossFadeOut


# ---------------------------------------------------------------------------
# Video configuration
# ---------------------------------------------------------------------------
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
BG_COLOR = (26, 26, 46)         # #1a1a2e — dark navy background
TITLE_COLOR = (255, 255, 255)   # White
CONTENT_COLOR = (220, 220, 230) # Slightly softer white
SLIDE_DURATION = 20              # Seconds per slide
FADE_DURATION = 0.5             # Fade transition duration


# ---------------------------------------------------------------------------
# Helper – render a single slide as a numpy image array
# ---------------------------------------------------------------------------
def _render_slide_frame(title: str, content: str) -> np.ndarray:
    """
    Draw a single slide (title + content) on a dark background using Pillow.
    Returns a numpy array (H, W, 3) suitable for MoviePy ImageClip.
    """
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # --- Load fonts (use system default if custom not available) ---
    try:
        title_font = ImageFont.truetype("arial.ttf", 48)
        content_font = ImageFont.truetype("arial.ttf", 32)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
            content_font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()

    # --- Wrap text to fit within the video width ---
    max_chars_title = 28
    max_chars_content = 38

    wrapped_title = textwrap.fill(title, width=max_chars_title)
    wrapped_content = textwrap.fill(content, width=max_chars_content)

    # --- Calculate positions ---
    # Title area: top 30% of frame
    title_y = 250
    # Content area: center of frame
    content_y = 550

    # --- Draw title (centered) ---
    title_bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (VIDEO_WIDTH - title_w) // 2
    draw.text(
        (title_x, title_y),
        wrapped_title,
        fill=TITLE_COLOR,
        font=title_font,
    )

    # --- Draw content (centered) ---
    content_bbox = draw.textbbox((0, 0), wrapped_content, font=content_font)
    content_w = content_bbox[2] - content_bbox[0]
    content_x = (VIDEO_WIDTH - content_w) // 2
    draw.text(
        (content_x, content_y),
        wrapped_content,
        fill=CONTENT_COLOR,
        font=content_font,
    )

    return np.array(img)


# ---------------------------------------------------------------------------
# Main – generate video from slides + audio
# ---------------------------------------------------------------------------
def generate_video(slides: list, audio_path: str, output_path: str) -> str:
    """
    Generate a vertical MP4 video from slide data and an audio file.

    Args:
        slides: List of dicts, each with 'title' and 'content' keys.
        audio_path: Path to the MP3 audio file.
        output_path: Path where the final MP4 video will be saved.

    Returns:
        The output_path on success.
    """
    print(f"[VIDEO] Generating video with {len(slides)} slides...", flush=True)

    # --- Build individual slide clips ---
    slide_clips = []
    for i, slide in enumerate(slides):
        title = slide.get("title", f"Slide {i + 1}")
        content = slide.get("content", "")

        frame = _render_slide_frame(title, content)
        clip = ImageClip(frame, duration=SLIDE_DURATION)

        # Apply fade-in and fade-out transitions
        clip = clip.with_effects([
            CrossFadeIn(FADE_DURATION),
            CrossFadeOut(FADE_DURATION),
        ])

        slide_clips.append(clip)
        print(f"[VIDEO]   Slide {i + 1}/{len(slides)}: \"{title}\"", flush=True)

    # --- Concatenate all slides ---
    video = concatenate_videoclips(slide_clips, method="compose")
    video_duration = video.duration
    print(f"[VIDEO] Total video duration: {video_duration:.1f}s", flush=True)

    # --- Add audio track ---
    try:
        audio = AudioFileClip(audio_path)

        # Trim or loop audio to match video length
        if audio.duration > video_duration:
            # Trim audio to video length
            audio = audio.subclipped(0, video_duration)
        elif audio.duration < video_duration:
            # Loop audio to fill video duration
            loops_needed = int(video_duration / audio.duration) + 1
            audio_clips = [
                audio.with_start(i * audio.duration)
                for i in range(loops_needed)
            ]
            audio = CompositeAudioClip(audio_clips).with_duration(video_duration)

        video = video.with_audio(audio)
        print(f"[VIDEO] Audio track added.", flush=True)
    except Exception as e:
        print(f"[VIDEO] WARNING: Could not add audio: {e}. Video will be silent.", flush=True)

    # --- Export as MP4 ---
    print(f"[VIDEO] Exporting to {output_path}...", flush=True)
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    # --- Cleanup ---
    video.close()
    print(f"[VIDEO] Video saved successfully: {output_path}", flush=True)
    return output_path
