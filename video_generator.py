"""
video_generator.py - Dual-pipeline video generation.

Two rendering modes:
    1. Manim pipeline    — for math/equation-heavy content (animated text scenes)
    2. Documentary pipeline — for general content (AI images + Ken Burns + teacher overlay)

Both pipelines produce a silent MP4, then compose audio with MoviePy.

Requirements:
    - manim (Community Edition) — for math pipeline
    - moviepy — for documentary pipeline + audio compositing
    - Pillow (PIL) — for image processing
    - FFmpeg (bundled via imageio-ffmpeg)
"""

import os
import uuid
import tempfile
import textwrap
import math

from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
import numpy as np

# ============================================================================
# Constants
# ============================================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FRAME_RATE = 30

# Color palette
BG_COLOR_HEX = "#1a1a2e"
ACCENT_COLOR_HEX = "#e94560"
ACCENT_SECONDARY_HEX = "#0f3460"
TITLE_COLOR = (255, 255, 255)
CONTENT_COLOR = (224, 224, 232)

# Documentary pipeline timing
TRANSITION_DURATION = 0.7   # Crossfade between slides
KEN_BURNS_ZOOM = 1.15       # Max zoom factor for Ken Burns effect
MIN_HOLD_TIME = 2.0         # Minimum slide duration


# ============================================================================
# Documentary Pipeline (General Content)
# ============================================================================

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _create_gradient_overlay(width: int, height: int) -> PILImage.Image:
    """Create a vertical gradient overlay (transparent top → dark bottom).

    Used to darken the lower portion of background images for text readability.
    """
    overlay = PILImage.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Gradient starts at 40% from top → fully dark at bottom
    gradient_start = int(height * 0.4)
    for y in range(gradient_start, height):
        progress = (y - gradient_start) / (height - gradient_start)
        alpha = int(200 * progress)  # Max 200/255 opacity
        draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))

    return overlay


def _create_slide_frame(
    bg_image_path: str | None,
    teacher_image_path: str | None,
    title: str,
    content: str,
    slide_num: int,
    total_slides: int,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
) -> PILImage.Image:
    """Compose a single slide frame as a PIL Image.

    Layout (portrait 1080x1920):
        - Full-screen background image (or solid color fallback)
        - Gradient overlay for text readability
        - Teacher character on the left side (bottom area)
        - Title text (top-right area)
        - Content text (middle-right area)
        - Slide progress indicator (bottom)
    """
    bg_color = _hex_to_rgb(BG_COLOR_HEX)

    # === Background ===
    if bg_image_path and os.path.exists(bg_image_path):
        bg = PILImage.open(bg_image_path).convert('RGBA')
        # Resize to fill the frame (cover mode)
        bg_ratio = max(width / bg.width, height / bg.height)
        new_size = (int(bg.width * bg_ratio), int(bg.height * bg_ratio))
        bg = bg.resize(new_size, PILImage.LANCZOS)
        # Center crop
        left = (bg.width - width) // 2
        top = (bg.height - height) // 2
        bg = bg.crop((left, top, left + width, top + height))
        # Apply slight blur for depth-of-field effect
        bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
    else:
        bg = PILImage.new('RGBA', (width, height), (*bg_color, 255))

    # === Gradient overlay ===
    gradient = _create_gradient_overlay(width, height)
    bg = PILImage.alpha_composite(bg, gradient)

    # Also add a top gradient for title readability
    top_overlay = PILImage.new('RGBA', (width, height), (0, 0, 0, 0))
    top_draw = ImageDraw.Draw(top_overlay)
    for y in range(0, int(height * 0.25)):
        progress = 1.0 - (y / (height * 0.25))
        alpha = int(150 * progress)
        top_draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))
    bg = PILImage.alpha_composite(bg, top_overlay)

    draw = ImageDraw.Draw(bg)

    # === Try to load fonts (use defaults if not available) ===
    try:
        title_font = ImageFont.truetype("arial.ttf", 52)
        content_font = ImageFont.truetype("arial.ttf", 32)
        small_font = ImageFont.truetype("arial.ttf", 24)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 52)
            content_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
            small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

    # === Teacher overlay (left side, bottom area) ===
    teacher_area_width = int(width * 0.35)
    if teacher_image_path and os.path.exists(teacher_image_path):
        teacher = PILImage.open(teacher_image_path).convert('RGBA')
        # Resize teacher to fit the left area
        teacher_height = int(height * 0.45)
        teacher_ratio = min(teacher_area_width / teacher.width, teacher_height / teacher.height)
        new_teacher_size = (int(teacher.width * teacher_ratio), int(teacher.height * teacher_ratio))
        teacher = teacher.resize(new_teacher_size, PILImage.LANCZOS)
        # Position: bottom-left
        teacher_x = int(width * 0.02)
        teacher_y = height - teacher.height - int(height * 0.08)
        bg.paste(teacher, (teacher_x, teacher_y), teacher)

    # === Text area (right side) ===
    text_left = int(width * 0.08)
    text_right = int(width * 0.92)
    text_width = text_right - text_left

    # === Accent bar (top decoration) ===
    accent_color = _hex_to_rgb(ACCENT_COLOR_HEX)
    bar_y = int(height * 0.08)
    draw.rectangle(
        [(text_left, bar_y), (text_left + int(text_width * 0.3), bar_y + 4)],
        fill=(*accent_color, 255),
    )

    # === Title ===
    wrapped_title = textwrap.fill(title, width=28)
    title_y = bar_y + 20
    draw.multiline_text(
        (text_left, title_y),
        wrapped_title,
        fill=(255, 255, 255, 255),
        font=title_font,
        spacing=8,
    )

    # Calculate title height for positioning content below it
    title_bbox = draw.multiline_textbbox(
        (text_left, title_y), wrapped_title, font=title_font, spacing=8
    )
    title_bottom = title_bbox[3]

    # === Content card (semi-transparent background behind content) ===
    content_y = title_bottom + 40
    wrapped_content = textwrap.fill(content, width=35)

    content_bbox = draw.multiline_textbbox(
        (text_left + 20, content_y + 20), wrapped_content, font=content_font, spacing=10
    )

    # Draw card background
    card_padding = 25
    card = PILImage.new('RGBA', (width, height), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle(
        [
            (text_left, content_y),
            (text_right, content_bbox[3] + card_padding + 20),
        ],
        radius=15,
        fill=(0, 0, 0, 100),
    )
    bg = PILImage.alpha_composite(bg, card)
    draw = ImageDraw.Draw(bg)

    # Draw content text
    draw.multiline_text(
        (text_left + 20, content_y + 20),
        wrapped_content,
        fill=(*CONTENT_COLOR, 255),
        font=content_font,
        spacing=10,
    )

    # === Slide progress dots (bottom center) ===
    dot_y = height - int(height * 0.04)
    dot_spacing = 24
    total_dot_width = total_slides * dot_spacing
    dot_start_x = (width - total_dot_width) // 2

    for j in range(total_slides):
        dot_x = dot_start_x + j * dot_spacing
        dot_color = accent_color if j == slide_num else (80, 80, 80)
        draw.ellipse(
            [(dot_x, dot_y), (dot_x + 10, dot_y + 10)],
            fill=(*dot_color, 255),
        )

    return bg.convert('RGB')


def _apply_ken_burns(clip, zoom_start=1.0, zoom_end=KEN_BURNS_ZOOM):
    """Apply Ken Burns (slow zoom-in) effect to an ImageClip.

    Creates a smooth zoom animation by resizing and cropping each frame.
    """
    w, h = clip.size
    duration = clip.duration

    def effect(get_frame, t):
        frame = get_frame(t)
        progress = t / duration if duration > 0 else 0
        current_zoom = zoom_start + (zoom_end - zoom_start) * progress

        # Calculate crop dimensions
        new_w = int(w / current_zoom)
        new_h = int(h / current_zoom)

        # Center crop
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        x2 = x1 + new_w
        y2 = y1 + new_h

        cropped = frame[y1:y2, x1:x2]

        # Resize back to original dimensions
        from PIL import Image as PILImg
        pil_img = PILImg.fromarray(cropped)
        pil_img = pil_img.resize((w, h), PILImg.LANCZOS)
        return np.array(pil_img)

    return clip.transform(effect)


def generate_documentary_video(
    slides: list,
    slide_images: list[str | None],
    teacher_image: str | None,
    slide_durations: list[float],
    audio_path: str,
    output_path: str,
) -> str:
    """Generate a documentary-style video with AI images and teacher overlay.

    Args:
        slides: List of slide dicts with 'title', 'content'.
        slide_images: List of background image paths per slide (can contain None).
        teacher_image: Path to teacher character image (or None).
        slide_durations: Per-slide audio durations in seconds.
        audio_path: Path to combined audio file.
        output_path: Path for final output video.

    Returns:
        Path to the generated video file.
    """
    print(f"[DOCUMENTARY] Starting documentary video ({len(slides)} slides)...", flush=True)

    temp_dir = tempfile.mkdtemp(prefix="documentary_")
    slide_clips = []

    for i, slide_data in enumerate(slides):
        title = slide_data.get("title", f"Slide {i + 1}")
        content = slide_data.get("content", "")
        bg_path = slide_images[i] if i < len(slide_images) else None
        duration = max(slide_durations[i], MIN_HOLD_TIME)

        print(f"[DOCUMENTARY] Creating slide {i + 1}/{len(slides)}: \"{title}\" ({duration:.1f}s)", flush=True)

        # Create the composed frame
        frame = _create_slide_frame(
            bg_image_path=bg_path,
            teacher_image_path=teacher_image,
            title=title,
            content=content,
            slide_num=i,
            total_slides=len(slides),
        )

        # Save frame as temp image
        frame_path = os.path.join(temp_dir, f"frame_{i}.png")
        frame.save(frame_path, quality=95)

        # Create video clip from the frame with Ken Burns
        clip = ImageClip(frame_path, duration=duration)
        clip = _apply_ken_burns(clip, zoom_start=1.0, zoom_end=KEN_BURNS_ZOOM)

        slide_clips.append(clip)

    # Concatenate clips with crossfade transitions
    print(f"[DOCUMENTARY] Compositing {len(slide_clips)} clips with transitions...", flush=True)

    if len(slide_clips) > 1:
        # Build final with crossfade transitions
        final_clips = [slide_clips[0]]
        for j in range(1, len(slide_clips)):
            # Apply crossfade: each clip starts TRANSITION_DURATION before the previous ends
            final_clips.append(
                slide_clips[j].with_start(
                    sum(slide_durations[:j]) - TRANSITION_DURATION * j
                ).with_effects([
                    # MoviePy crossfade
                ])
            )

        # Use CompositeVideoClip for overlapping transitions
        total_duration = sum(slide_durations) - TRANSITION_DURATION * (len(slide_clips) - 1)
        final_video = CompositeVideoClip(
            final_clips,
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        ).with_duration(total_duration)
    else:
        final_video = slide_clips[0]

    # Write silent video
    silent_path = os.path.join(temp_dir, "silent_documentary.mp4")
    final_video.write_videofile(
        silent_path,
        fps=FRAME_RATE,
        codec="libx264",
        logger="bar",
    )
    final_video.close()
    for clip in slide_clips:
        clip.close()

    print(f"[DOCUMENTARY] Silent video: {silent_path}", flush=True)

    # Compose with audio
    _compose_audio(silent_path, audio_path, output_path)

    return output_path


# ============================================================================
# Manim Pipeline (Math Content) — Preserved from original
# ============================================================================

def _build_manim_scene(slides: list, slide_durations: list[float]):
    """Dynamically construct a Manim Scene class for math content."""
    from manim import (
        Scene, Text, RoundedRectangle, Line, VGroup, Dot,
        config as manim_config,
        Write, FadeIn, FadeOut, GrowFromCenter,
        UP, DOWN, LEFT, RIGHT, ORIGIN, ManimColor,
    )

    # Animation timing
    ANIM_IN_TIME = 1.5
    ANIM_OUT_TIME = 0.5
    INTER_SLIDE_GAP = 0.2

    class MicroLearningScene(Scene):
        def construct(self):
            total_slides = len(slides)

            for i, slide_data in enumerate(slides):
                title_text = slide_data.get("title", f"Slide {i + 1}")
                content_text = slide_data.get("content", "")
                audio_duration = slide_durations[i]

                hold_time = max(
                    audio_duration - ANIM_IN_TIME - ANIM_OUT_TIME,
                    1.0,
                )

                # Background card
                card = RoundedRectangle(
                    corner_radius=0.3, width=12, height=6,
                    fill_color=ManimColor("#0f3460"),
                    fill_opacity=0.15,
                    stroke_color=ManimColor("#0f3460"),
                    stroke_opacity=0.3, stroke_width=1.5,
                )
                card.move_to(ORIGIN).shift(UP * 0.5)

                # Title
                wrapped_title = textwrap.fill(title_text, width=30)
                title = Text(
                    wrapped_title, font_size=44,
                    color=ManimColor("#ffffff"), weight="BOLD",
                ).move_to(ORIGIN).shift(UP * 2.5)

                # Accent underline
                accent_bar = Line(
                    start=LEFT * 2, end=RIGHT * 2,
                    color=ManimColor("#e94560"), stroke_width=4,
                ).next_to(title, DOWN, buff=0.3)

                # Content
                wrapped_content = textwrap.fill(content_text, width=40)
                content = Text(
                    wrapped_content, font_size=28,
                    color=ManimColor("#e0e0e8"), line_spacing=0.6,
                ).next_to(accent_bar, DOWN, buff=0.6)

                # Slide dots
                dots = VGroup()
                for j in range(total_slides):
                    dot = Dot(
                        radius=0.06,
                        color=ManimColor("#e94560") if j == i else ManimColor("#555555"),
                    )
                    dots.add(dot)
                dots.arrange(RIGHT, buff=0.2)
                dots.move_to(ORIGIN).shift(DOWN * 3.2)

                # Animate in
                self.play(FadeIn(card, shift=UP * 0.3), FadeIn(dots), run_time=0.4)
                self.play(Write(title), run_time=0.6)
                self.play(GrowFromCenter(accent_bar), run_time=0.2)
                self.play(FadeIn(content, shift=UP * 0.2), run_time=0.3)

                self.wait(hold_time)

                # Animate out
                self.play(
                    FadeOut(card), FadeOut(title), FadeOut(accent_bar),
                    FadeOut(content), FadeOut(dots), run_time=0.5,
                )
                self.wait(INTER_SLIDE_GAP)

    return MicroLearningScene


def _render_manim_scene(slides: list, slide_durations: list[float], temp_dir: str) -> str:
    """Render a Manim scene to MP4."""
    from manim import config as manim_config, ManimColor

    manim_config.pixel_width = VIDEO_WIDTH
    manim_config.pixel_height = VIDEO_HEIGHT
    manim_config.frame_rate = FRAME_RATE
    manim_config.media_dir = temp_dir
    manim_config.background_color = ManimColor(BG_COLOR_HEX)
    manim_config.quality = "high_quality"
    manim_config.disable_caching = True

    SceneClass = _build_manim_scene(slides, slide_durations)
    scene = SceneClass()
    scene.render()

    output_path = str(scene.renderer.file_writer.movie_file_path)
    print(f"[MANIM] Rendered to: {output_path}", flush=True)
    return output_path


# ============================================================================
# Audio Compositing (shared by both pipelines)
# ============================================================================

def _compose_audio(video_path: str, audio_path: str, output_path: str):
    """Merge audio onto a silent video."""
    print(f"[AUDIO] Compositing audio onto video...", flush=True)

    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

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
    print(f"[AUDIO] Final video: {output_path}", flush=True)


# ============================================================================
# Public API — Unified entry point
# ============================================================================

def generate_video(
    slides: list,
    slide_durations: list[float],
    audio_path: str,
    output_path: str,
    content_type: str = "general",
    slide_images: list[str | None] | None = None,
    teacher_image: str | None = None,
) -> str:
    """Generate a micro-learning video.

    Routes to the appropriate pipeline based on content_type:
        - "math"    → Manim animated scenes (text + equations)
        - "general" → Documentary style (AI images + teacher + Ken Burns)

    Args:
        slides: List of slide dicts with 'title' and 'content'.
        slide_durations: Per-slide audio durations in seconds.
        audio_path: Path to combined narration audio.
        output_path: Path for final output video.
        content_type: "math" or "general".
        slide_images: (general only) Background image paths per slide.
        teacher_image: (general only) Teacher character image path.

    Returns:
        Path to the generated video file.
    """
    print(f"[VIDEO] Pipeline: {content_type} | {len(slides)} slides", flush=True)

    if content_type == "math":
        # Manim pipeline
        print(f"[VIDEO] Using Manim pipeline for math content.", flush=True)
        temp_dir = tempfile.mkdtemp(prefix="manim_render_")
        try:
            silent_video = _render_manim_scene(slides, slide_durations, temp_dir)
            _compose_audio(silent_video, audio_path, output_path)
        except Exception as e:
            print(f"[VIDEO] ERROR in Manim pipeline: {e}", flush=True)
            raise
    else:
        # Documentary pipeline
        print(f"[VIDEO] Using documentary pipeline for general content.", flush=True)
        generate_documentary_video(
            slides=slides,
            slide_images=slide_images or [None] * len(slides),
            teacher_image=teacher_image,
            slide_durations=slide_durations,
            audio_path=audio_path,
            output_path=output_path,
        )

    print(f"[VIDEO] Generation complete: {output_path}", flush=True)
    return output_path
