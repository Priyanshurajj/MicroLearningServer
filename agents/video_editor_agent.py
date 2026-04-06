import json
import os
import logging
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from moviepy import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    ColorClip,
    CompositeVideoClip,
)
import moviepy.video.fx as vfx
import moviepy.audio.fx as afx
import imageio_ffmpeg

from .config import ROUTING_MODEL, OUTPUT_DIR, OVERLAY_FONT_PATH

logger = logging.getLogger("EduReelADK")

REEL_WIDTH = 1080
REEL_HEIGHT = 1920
FPS = 30

# Text overlay constants
OVERLAY_FONT_SIZE = 80
HIGHLIGHT_RGBA = (255, 220, 0, 245)
HIGHLIGHT_TEXT_RGBA = (140, 70, 0, 255)   # warm amber on yellow
TEXT_RGBA = (15, 15, 15, 255)             # near-black on frosted panel
PANEL_RGBA = (255, 255, 255, 185)         # frosted white panel behind text block
OVERLAY_Y_RATIO = 0.42                    # vertically centered
LINE_SPACING = 28

# Concept map overlay position (top-right, 20px margin)
CONCEPT_MAP_W = 240
CONCEPT_MAP_MARGIN = 20


def compose_final_video(tool_context: ToolContext) -> dict:
    """Reads enhanced_script, tts_output, qc_output, image_output, concept_map_output
    from session state and composes the final reel MP4."""
    try:
        script = json.loads(tool_context.state.get("enhanced_script", "{}"))
        tts_data = json.loads(tool_context.state.get("tts_output", "{}"))
        qc_data = json.loads(tool_context.state.get("qc_output", "{}"))
        image_data = json.loads(tool_context.state.get("image_output", "{}"))
        concept_map_data = json.loads(
            tool_context.state.get("concept_map_output", "{}")
        )
    except (json.JSONDecodeError, TypeError) as e:
        return {"status": "error", "error": f"Invalid JSON in state: {e}"}

    run_id = script.get("run_id", qc_data.get("run_id", "default"))
    output_path = os.path.join(OUTPUT_DIR, run_id, "final_reel.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    segments = sorted(script.get("segments", []), key=lambda s: s["segment_id"])

    # ── Build lookup maps ──

    # Audio: segment_id → audio metadata
    audio_map: dict[int, dict] = {}
    for s in tts_data.get("audio_segments", []):
        s["audio_file_path"] = os.path.normpath(s.get("audio_file_path", ""))
        audio_map[s["segment_id"]] = s

    # Manim videos: segment_id → qc asset (has video_path + optional background_image_path)
    manim_map: dict[int, dict] = {}
    for a in qc_data.get("qc_assets", []):
        if "video_path" in a:
            a["video_path"] = os.path.normpath(a["video_path"])
        manim_map[a["segment_id"]] = a

    # General images: segment_id → image asset
    image_map: dict[int, dict] = {}
    for img in image_data.get("images", []):
        if img.get("image_file_path"):
            img["image_file_path"] = os.path.normpath(img["image_file_path"])
        image_map[img["segment_id"]] = img

    # Concept map frames: segment_id (str) → PNG path
    concept_frames: dict[str, str] = concept_map_data.get("frames", {})

    clips = []
    timeline = []
    current_time = 0.0

    for seg in segments:
        seg_id = seg["segment_id"]
        audio_info = audio_map.get(seg_id, {})
        manim_asset = manim_map.get(seg_id)
        image_asset = image_map.get(seg_id)

        audio_path = audio_info.get("audio_file_path", "")
        audio_duration = audio_info.get(
            "duration_seconds", seg.get("duration_seconds", 5.0)
        )
        concept_frame_path = concept_frames.get(str(seg_id), "")

        try:
            clip = _create_segment_clip(
                seg, manim_asset, image_asset,
                audio_path, audio_duration, concept_frame_path,
            )
            if clip is not None:
                clips.append(clip)
                timeline.append({
                    "segment_id": seg_id,
                    "segment_type": seg.get("segment_type", "general"),
                    "visual_type": (
                        "manim" if manim_asset else
                        "image" if image_asset else "fallback"
                    ),
                    "start_time": round(current_time, 2),
                    "end_time": round(current_time + audio_duration, 2),
                    "duration_seconds": round(audio_duration, 2),
                })
                current_time += audio_duration
        except Exception as e:
            logger.error(f"Failed to create clip for segment {seg_id}: {e}")
            fallback = _create_fallback_clip(audio_duration)
            if fallback:
                clips.append(fallback)
                current_time += audio_duration

    if not clips:
        return {"status": "error", "error": "No clips were created."}

    try:
        final_video = concatenate_videoclips(clips, method="compose")

        temp_video = os.path.join(os.path.dirname(output_path), "temp_video.mp4")
        temp_audio = os.path.join(os.path.dirname(output_path), "temp_audio.mp3")

        final_video.without_audio().write_videofile(
            temp_video,
            fps=FPS,
            codec="libx264",
            logger="bar",
        )

        if final_video.audio is not None:
            final_video.audio.write_audiofile(temp_audio, logger="bar")

        final_video.close()
        for clip in clips:
            clip.close()

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        if os.path.exists(temp_audio):
            ffmpeg_cmd = [
                ffmpeg_exe, "-y",
                "-i", temp_video,
                "-i", temp_audio,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path,
            ]
        else:
            ffmpeg_cmd = [
                ffmpeg_exe, "-y",
                "-i", temp_video,
                "-c:v", "copy",
                output_path,
            ]

        result = subprocess.run(
            ffmpeg_cmd, capture_output=True, text=True, timeout=300
        )

        for f in [temp_video, temp_audio]:
            if os.path.exists(f):
                os.remove(f)

        if result.returncode != 0:
            logger.error(f"FFmpeg merge failed: {result.stderr[:500]}")
            return {"status": "error", "error": f"FFmpeg merge failed: {result.stderr[:300]}"}

        logger.info(f"Final video composed: {output_path} ({current_time:.1f}s)")

        video_result = {
            "video_file_path": os.path.abspath(output_path),
            "duration_seconds": round(current_time, 2),
            "resolution": f"{REEL_WIDTH}x{REEL_HEIGHT}",
            "format": "mp4",
            "fps": FPS,
            "timeline": timeline,
            "total_clips": len(timeline),
            "general_clips": sum(1 for t in timeline if t["segment_type"] == "general"),
            "manim_clips": sum(1 for t in timeline if t["segment_type"] == "manim"),
        }

        video_output_json = json.dumps(video_result)
        tool_context.state["video_output"] = video_output_json
        return {"status": "success", "video_output": video_output_json}

    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        return {"status": "error", "error": str(e)}


def _create_segment_clip(
    seg: dict,
    manim_asset: dict | None,
    image_asset: dict | None,
    audio_path: str,
    duration: float,
    concept_frame_path: str,
):
    """Builds a single segment clip with optional background, text overlay, and concept map."""

    # ── 1. Base clip ──
    if manim_asset and manim_asset.get("status") == "rendered":
        video_path = manim_asset.get("video_path", "")
        bg_path = manim_asset.get("background_image_path", "")

        if video_path and os.path.exists(video_path):
            if bg_path and os.path.exists(bg_path):
                clip = _create_manim_with_background(video_path, bg_path, duration)
            else:
                manim_clip = VideoFileClip(video_path)
                manim_clip = manim_clip.resized(height=REEL_HEIGHT)
                if manim_clip.w != REEL_WIDTH:
                    manim_clip = manim_clip.resized(width=REEL_WIDTH)
                clip = manim_clip
        else:
            clip = _create_fallback_clip(duration)

    elif image_asset and image_asset.get("status") == "generated":
        image_path = image_asset.get("image_file_path", "")
        if image_path and os.path.exists(image_path):
            clip = ImageClip(image_path, duration=duration)
            clip = clip.resized(height=REEL_HEIGHT)
            if clip.w != REEL_WIDTH:
                clip = clip.resized(width=REEL_WIDTH)
            clip = clip.with_duration(duration)
        else:
            clip = _create_fallback_clip(duration)
    else:
        clip = _create_fallback_clip(duration)

    # ── 2. Text overlay (PIL-rendered, only if segment specifies it) ──
    text_overlay = seg.get("text_overlay")
    if text_overlay and clip is not None:
        try:
            overlay_clip = _render_text_overlay_pil(
                text_overlay, REEL_WIDTH, REEL_HEIGHT, clip.duration
            )
            clip = CompositeVideoClip(
                [clip, overlay_clip],
                size=(REEL_WIDTH, REEL_HEIGHT),
            )
        except Exception as e:
            logger.warning(f"Text overlay failed for segment {seg.get('segment_id')}: {e}")

    # ── 3. Concept map overlay (top-right corner) ──
    if concept_frame_path and os.path.exists(concept_frame_path) and clip is not None:
        try:
            map_clip = ImageClip(concept_frame_path).with_duration(clip.duration)
            x_pos = REEL_WIDTH - CONCEPT_MAP_W - CONCEPT_MAP_MARGIN
            clip = CompositeVideoClip(
                [clip, map_clip.with_position((x_pos, CONCEPT_MAP_MARGIN))],
                size=(REEL_WIDTH, REEL_HEIGHT),
            )
        except Exception as e:
            logger.warning(
                f"Concept map overlay failed for segment {seg.get('segment_id')}: {e}"
            )

    # ── 4. Attach audio ──
    if clip and audio_path and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        if abs(clip.duration - audio.duration) > 0.5:
            clip = clip.with_duration(audio.duration)
        clip = clip.with_audio(audio)

    # ── 5. Smooth fade transitions ──
    if clip is not None:
        fade = min(0.3, clip.duration / 4)
        clip = clip.with_effects([vfx.FadeIn(fade), vfx.FadeOut(fade)])
        if clip.audio is not None:
            clip.audio = clip.audio.with_effects([afx.AudioFadeIn(fade), afx.AudioFadeOut(fade)])

    return clip


def _create_manim_with_background(
    video_path: str, bg_path: str, duration: float
):
    """Composites a transparent Manim animation natively over an unblurred background image."""
    pil_bg = Image.open(bg_path).convert("RGB")
    pil_bg = pil_bg.resize((REEL_WIDTH, REEL_HEIGHT), Image.LANCZOS)
    # No blurring or massive darkening — keep it cinematic. We dim slightly (85%) for contrast.
    bg_array = (np.array(pil_bg) * 0.85).astype(np.uint8)

    bg_clip = ImageClip(bg_array).with_duration(duration)

    manim_clip = VideoFileClip(video_path, has_mask=True)
    
    # Scale Manim to fit if the aspect ratios don't match, keeping it large
    if manim_clip.w != REEL_WIDTH:
        scale = min(REEL_WIDTH / manim_clip.w, REEL_HEIGHT / manim_clip.h)
        manim_clip = manim_clip.resized(scale)

    # If the Manim animation finishes before the audio, freeze it on the last frame
    if manim_clip.duration < duration:
        try:
            t_last = max(0, manim_clip.duration - 0.1)
            last_frame = manim_clip.get_frame(t_last)
            freeze_dur = duration - manim_clip.duration
            freeze_clip = ImageClip(last_frame).with_duration(freeze_dur)

            if getattr(manim_clip, "mask", None) is not None:
                last_mask = manim_clip.mask.get_frame(t_last)
                freeze_clip = freeze_clip.with_mask(ImageClip(last_mask, is_mask=True))

            manim_clip = concatenate_videoclips([manim_clip, freeze_clip], method="compose")
        except Exception as e:
            logger.warning(f"Could not extend transparent Manim clip duration: {e}")

    return CompositeVideoClip(
        [bg_clip, manim_clip.with_position("center")],
        size=(REEL_WIDTH, REEL_HEIGHT),
    ).with_duration(duration)


def _render_text_overlay_pil(
    text_overlay: dict, width: int, height: int, duration: float
) -> ImageClip:
    """Renders a text overlay with frosted panel and tight yellow word highlights."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(OVERLAY_FONT_PATH, OVERLAY_FONT_SIZE)
    except (OSError, IOError):
        font = ImageFont.load_default()

    lines = text_overlay.get("lines", [])
    highlight_words = {w.lower().strip(".,!?") for w in text_overlay.get("highlight_words", [])}

    h_pad = 12   # horizontal padding inside highlight rect
    v_pad = 10   # vertical padding inside highlight rect
    panel_margin = 20

    # Measure line heights/widths for panel sizing
    sample_bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_h = sample_bbox[3] - sample_bbox[1]

    total_block_h = len(lines) * (line_h + LINE_SPACING) - LINE_SPACING
    block_top = int(height * OVERLAY_Y_RATIO) - total_block_h // 2

    max_line_w = 0
    for line in lines:
        words = line.split()
        lw = sum(
            draw.textbbox((0, 0), w + " ", font=font)[2]
            - draw.textbbox((0, 0), w + " ", font=font)[0]
            for w in words
        )
        max_line_w = max(max_line_w, lw)

    panel_x0 = (width - max_line_w) // 2 - panel_margin
    panel_y0 = block_top - panel_margin
    panel_x1 = (width + max_line_w) // 2 + panel_margin
    panel_y1 = block_top + total_block_h + panel_margin
    draw.rounded_rectangle(
        [panel_x0, panel_y0, panel_x1, panel_y1],
        radius=18,
        fill=PANEL_RGBA,
    )

    y = block_top
    for line in lines:
        words = line.split()

        # Advance widths (word + space) for x-positioning
        advance_widths = []
        for word in words:
            bbox = draw.textbbox((0, 0), word + " ", font=font)
            advance_widths.append(bbox[2] - bbox[0])

        total_w = sum(advance_widths)
        x = (width - total_w) // 2

        for word, adv_w in zip(words, advance_widths):
            clean = word.lower().strip(".,!?")

            # Word-only width for tight highlight rect
            word_bbox = draw.textbbox((0, 0), word, font=font)
            word_only_w = word_bbox[2] - word_bbox[0]
            word_h = word_bbox[3] - word_bbox[1]

            if clean in highlight_words:
                rect = [
                    x - h_pad, y - v_pad,
                    x + word_only_w + h_pad, y + word_h + v_pad,
                ]
                draw.rounded_rectangle(rect, radius=8, fill=HIGHLIGHT_RGBA)
                draw.text((x, y), word, font=font, fill=HIGHLIGHT_TEXT_RGBA)
            else:
                draw.text((x, y), word, font=font, fill=TEXT_RGBA)

            x += adv_w

        y += line_h + LINE_SPACING

    return ImageClip(np.array(img)).with_duration(duration)


def _create_fallback_clip(duration: float):
    return ColorClip(
        size=(REEL_WIDTH, REEL_HEIGHT),
        color=(20, 20, 30),
        duration=duration,
    )


video_editor_agent = Agent(
    name="video_editor_agent",
    model=ROUTING_MODEL,
    description=(
        "Composes the final educational reel by stitching Manim clips and images "
        "with TTS audio, text overlays, concept map overlays, and smooth transitions."
    ),
    instruction=(
        "You are the Video Editor Agent. "
        "Call the compose_final_video tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[compose_final_video],
)
