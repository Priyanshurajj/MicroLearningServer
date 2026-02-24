"""
video_generator.py - Animated video generation using Manim Community Edition.

Creates a vertical (1080x1920) animated MP4 video where each slide features:
    - Dark gradient background
    - Animated title (Write effect)
    - Decorative accent bar
    - Animated content text (FadeIn effect)
    - Slide number indicator
    - Duration-matched to per-slide audio for perfect sync

Audio is composed onto the video using MoviePy after Manim rendering.

Requirements:
    - manim (Community Edition)
    - moviepy (for audio compositing)
    - FFmpeg (bundled via imageio-ffmpeg)
"""

import os
import uuid
import tempfile
import textwrap

from manim import (
    Scene,
    Text,
    Rectangle,
    RoundedRectangle,
    Line,
    VGroup,
    Dot,
    config,
    Write,
    FadeIn,
    FadeOut,
    GrowFromCenter,
    Create,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
    WHITE,
    GRAY,
    ManimColor,
)
from moviepy import (
    VideoFileClip,
    AudioFileClip,
)


# ---------------------------------------------------------------------------
# Video configuration
# ---------------------------------------------------------------------------
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FRAME_RATE = 30
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
ACCENT_SECONDARY = "#0f3460"
TITLE_COLOR = "#ffffff"
CONTENT_COLOR = "#e0e0e8"

# Animation timing (these are subtracted from total slide duration to get hold time)
ANIM_IN_TIME = 1.5     # Title write + accent bar + content fade in
ANIM_OUT_TIME = 0.5    # Fade out
INTER_SLIDE_GAP = 0.2  # Pause between slides
MIN_HOLD_TIME = 1.0    # Minimum time to hold a slide on screen


def _build_scene_class(slides: list, slide_durations: list[float]):
    """
    Dynamically construct a Manim Scene class with duration-matched slides.

    Args:
        slides: List of slide dicts with 'title' and 'content'.
        slide_durations: Per-slide audio durations in seconds.
    """

    class MicroLearningScene(Scene):
        def construct(self):
            total_slides = len(slides)

            for i, slide_data in enumerate(slides):
                title_text = slide_data.get("title", f"Slide {i + 1}")
                content_text = slide_data.get("content", "")
                audio_duration = slide_durations[i]

                # Calculate hold time = audio duration minus animation time
                hold_time = max(
                    audio_duration - ANIM_IN_TIME - ANIM_OUT_TIME,
                    MIN_HOLD_TIME,
                )

                # --- Background card ---
                card = RoundedRectangle(
                    corner_radius=0.3,
                    width=12,
                    height=6,
                    fill_color=ManimColor(ACCENT_SECONDARY),
                    fill_opacity=0.15,
                    stroke_color=ManimColor(ACCENT_SECONDARY),
                    stroke_opacity=0.3,
                    stroke_width=1.5,
                )
                card.move_to(ORIGIN).shift(UP * 0.5)

                # --- Title ---
                wrapped_title = textwrap.fill(title_text, width=30)
                title = Text(
                    wrapped_title,
                    font_size=44,
                    color=ManimColor(TITLE_COLOR),
                    weight="BOLD",
                ).move_to(ORIGIN).shift(UP * 2.5)

                # --- Accent underline bar ---
                accent_bar = Line(
                    start=LEFT * 2,
                    end=RIGHT * 2,
                    color=ManimColor(ACCENT_COLOR),
                    stroke_width=4,
                ).next_to(title, DOWN, buff=0.3)

                # --- Content text ---
                wrapped_content = textwrap.fill(content_text, width=40)
                content = Text(
                    wrapped_content,
                    font_size=28,
                    color=ManimColor(CONTENT_COLOR),
                    line_spacing=0.6,
                ).next_to(accent_bar, DOWN, buff=0.6)

                # --- Slide number dots ---
                dots = VGroup()
                for j in range(total_slides):
                    dot = Dot(
                        radius=0.06,
                        color=ManimColor(ACCENT_COLOR) if j == i else ManimColor("#555555"),
                    )
                    dots.add(dot)
                dots.arrange(RIGHT, buff=0.2)
                dots.move_to(ORIGIN).shift(DOWN * 3.2)

                # --- Animate in (~1.5s) ---
                self.play(
                    FadeIn(card, shift=UP * 0.3),
                    FadeIn(dots),
                    run_time=0.4,
                )
                self.play(Write(title), run_time=0.6)
                self.play(GrowFromCenter(accent_bar), run_time=0.2)
                self.play(FadeIn(content, shift=UP * 0.2), run_time=0.3)

                # --- Hold (matched to audio duration) ---
                self.wait(hold_time)

                # --- Animate out (~0.5s) ---
                self.play(
                    FadeOut(card),
                    FadeOut(title),
                    FadeOut(accent_bar),
                    FadeOut(content),
                    FadeOut(dots),
                    run_time=0.5,
                )

                # Brief gap between slides
                self.wait(INTER_SLIDE_GAP)

    return MicroLearningScene


def _render_manim_scene(slides: list, slide_durations: list[float], temp_dir: str) -> str:
    """
    Render the Manim scene to a silent MP4 file.
    """
    config.pixel_width = VIDEO_WIDTH
    config.pixel_height = VIDEO_HEIGHT
    config.frame_rate = FRAME_RATE
    config.media_dir = temp_dir
    config.background_color = ManimColor(BG_COLOR)
    config.quality = "high_quality"
    config.disable_caching = True

    SceneClass = _build_scene_class(slides, slide_durations)
    scene = SceneClass()
    scene.render()

    output_path = str(scene.renderer.file_writer.movie_file_path)
    print(f"[VIDEO] Manim rendered to: {output_path}", flush=True)
    return output_path


def _compose_audio(video_path: str, audio_path: str, output_path: str):
    """
    Merge a Manim-rendered video with a TTS audio file using MoviePy.
    """
    print(f"[VIDEO] Compositing audio onto video...", flush=True)

    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # Trim audio if it's slightly longer than video (due to rounding)
    if audio.duration > video.duration:
        audio = audio.subclipped(0, video.duration)

    final = video.with_audio(audio)
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    final.close()
    video.close()
    print(f"[VIDEO] Final video with synced audio: {output_path}", flush=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_video(slides: list, slide_durations: list[float], audio_path: str, output_path: str) -> str:
    """
    Generate an animated vertical MP4 video with per-slide duration sync.

    Args:
        slides: List of dicts with 'title' and 'content' keys.
        slide_durations: Duration in seconds for each slide (from TTS).
        audio_path: Path to the concatenated TTS MP3.
        output_path: Path for the final MP4.

    Returns:
        The output_path on success.
    """
    print(f"[VIDEO] Starting Manim video generation ({len(slides)} slides)...", flush=True)
    for i, dur in enumerate(slide_durations):
        print(f"[VIDEO]   Slide {i+1}: {dur:.1f}s", flush=True)

    temp_dir = tempfile.mkdtemp(prefix="manim_render_")

    try:
        # Step 1: Render with Manim (duration-matched)
        print(f"[VIDEO] Step 1/2: Rendering animated slides with Manim...", flush=True)
        silent_video = _render_manim_scene(slides, slide_durations, temp_dir)

        # Step 2: Compose audio
        print(f"[VIDEO] Step 2/2: Compositing audio...", flush=True)
        _compose_audio(silent_video, audio_path, output_path)

        print(f"[VIDEO] Video generation complete: {output_path}", flush=True)
        return output_path

    except Exception as e:
        print(f"[VIDEO] ERROR during video generation: {e}", flush=True)
        raise
