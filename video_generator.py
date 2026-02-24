"""
video_generator.py - Animated video generation using Manim Community Edition.

Creates a vertical (1080×1920) animated MP4 video where each slide features:
    - Dark gradient background
    - Animated title (Write effect)
    - Decorative accent bar
    - Animated content text (FadeIn effect)
    - Slide number indicator
    - Smooth fade transitions between slides

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
    CompositeAudioClip,
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
SLIDE_HOLD_DURATION = 4     # Seconds to hold each slide (excluding animation time)


def _build_scene_class(slides: list):
    """
    Dynamically construct a Manim Scene class for the given slides.
    Returns the class (not an instance).
    """

    class MicroLearningScene(Scene):
        def construct(self):
            total_slides = len(slides)

            for i, slide_data in enumerate(slides):
                title_text = slide_data.get("title", f"Slide {i + 1}")
                content_text = slide_data.get("content", "")

                # --- Background card (subtle rounded rectangle) ---
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

                # --- Slide number indicator (dots) ---
                dots = VGroup()
                for j in range(total_slides):
                    dot = Dot(
                        radius=0.06,
                        color=ManimColor(ACCENT_COLOR) if j == i else ManimColor("#555555"),
                    )
                    dots.add(dot)
                dots.arrange(RIGHT, buff=0.2)
                dots.move_to(ORIGIN).shift(DOWN * 3.2)

                # --- Animations ---
                # Slide card appears
                self.play(
                    FadeIn(card, shift=UP * 0.3),
                    FadeIn(dots),
                    run_time=0.4,
                )

                # Title writes in
                self.play(Write(title), run_time=0.8)

                # Accent bar grows from center
                self.play(GrowFromCenter(accent_bar), run_time=0.3)

                # Content fades in
                self.play(FadeIn(content, shift=UP * 0.2), run_time=0.5)

                # Hold the slide
                self.wait(SLIDE_HOLD_DURATION)

                # Fade everything out
                self.play(
                    FadeOut(card),
                    FadeOut(title),
                    FadeOut(accent_bar),
                    FadeOut(content),
                    FadeOut(dots),
                    run_time=0.5,
                )

                # Brief pause between slides
                self.wait(0.2)

    return MicroLearningScene


def _render_manim_scene(slides: list, temp_dir: str) -> str:
    """
    Render the Manim scene to a silent MP4 file.

    Args:
        slides: List of slide dicts with 'title' and 'content'.
        temp_dir: Directory for Manim media output.

    Returns:
        Path to the rendered MP4 file.
    """
    # Configure Manim for vertical video
    config.pixel_width = VIDEO_WIDTH
    config.pixel_height = VIDEO_HEIGHT
    config.frame_rate = FRAME_RATE
    config.media_dir = temp_dir
    config.background_color = ManimColor(BG_COLOR)
    config.quality = "high_quality"
    config.disable_caching = True

    # Build and render the scene
    SceneClass = _build_scene_class(slides)
    scene = SceneClass()
    scene.render()

    # Get the output file path
    output_path = str(scene.renderer.file_writer.movie_file_path)
    print(f"[VIDEO] Manim rendered to: {output_path}", flush=True)
    return output_path


def _compose_audio(video_path: str, audio_path: str, output_path: str):
    """
    Merge a Manim-rendered video with a TTS audio file using MoviePy.
    Trims or loops the audio to match the video duration.

    Args:
        video_path: Path to the silent Manim video.
        audio_path: Path to the TTS audio file.
        output_path: Path for the final composited output.
    """
    print(f"[VIDEO] Compositing audio onto video...", flush=True)

    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    video_duration = video.duration

    # Trim or loop audio to match video length
    if audio.duration > video_duration:
        audio = audio.subclipped(0, video_duration)
    elif audio.duration < video_duration:
        loops_needed = int(video_duration / audio.duration) + 1
        audio_clips = [
            audio.with_start(i * audio.duration)
            for i in range(loops_needed)
        ]
        audio = CompositeAudioClip(audio_clips).with_duration(video_duration)

    # Set audio on video and export
    final = video.with_audio(audio)
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    # Cleanup
    final.close()
    video.close()
    print(f"[VIDEO] Final video with audio: {output_path}", flush=True)


# ---------------------------------------------------------------------------
# Public API – generate_video (same interface as before)
# ---------------------------------------------------------------------------
def generate_video(slides: list, audio_path: str, output_path: str) -> str:
    """
    Generate an animated vertical MP4 video from slide data with synced audio.

    Two-step process:
        1. Render animated slides using Manim → silent MP4
        2. Composite TTS audio onto the video using MoviePy

    Args:
        slides: List of dicts, each with 'title' and 'content' keys.
        audio_path: Path to the TTS MP3 audio file.
        output_path: Path where the final MP4 video will be saved.

    Returns:
        The output_path on success.
    """
    print(f"[VIDEO] Starting Manim video generation ({len(slides)} slides)...", flush=True)

    # Create a temp directory for Manim media
    temp_dir = tempfile.mkdtemp(prefix="manim_render_")

    try:
        # Step 1: Render with Manim
        print(f"[VIDEO] Step 1/2: Rendering animated slides with Manim...", flush=True)
        silent_video = _render_manim_scene(slides, temp_dir)

        # Step 2: Compose audio
        print(f"[VIDEO] Step 2/2: Compositing audio...", flush=True)
        _compose_audio(silent_video, audio_path, output_path)

        print(f"[VIDEO] Video generation complete: {output_path}", flush=True)
        return output_path

    except Exception as e:
        print(f"[VIDEO] ERROR during video generation: {e}", flush=True)
        raise
