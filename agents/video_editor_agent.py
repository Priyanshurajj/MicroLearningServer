"""
Video Editor Agent — uses MoviePy to compose the final educational reel
by stitching static images and Manim video clips with TTS audio narration.
"""
import json
import os
import logging

from google.adk.agents import Agent
from moviepy import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    ColorClip,
)

from .config import ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")

# Reel dimensions (vertical 9:16)
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
FPS = 30


def compose_final_video(script_json: str, tts_json: str, qc_output_json: str) -> dict:
    """Composes the final reel by combining images, Manim clips, and TTS audio."""
    try:
        script = json.loads(script_json)
        tts_data = json.loads(tts_json)
        qc_data = json.loads(qc_output_json)
    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"Invalid JSON provided to Video Editor: {e}"}

    run_id = script.get("run_id", qc_data.get("run_id", "default"))
    output_path = os.path.join(OUTPUT_DIR, run_id, "final_reel.mp4")

    # Build lookup maps
    segments = sorted(script.get("segments", []), key=lambda s: s["segment_id"])
    audio_map = {s["segment_id"]: s for s in tts_data.get("audio_segments", [])}
    asset_map = {a["segment_id"]: a for a in qc_data.get("qc_assets", [])}

    clips = []
    timeline = []
    current_time = 0.0

    for seg in segments:
        seg_id = seg["segment_id"]
        audio_info = audio_map.get(seg_id, {})
        asset_info = asset_map.get(seg_id, {})

        audio_path = audio_info.get("audio_file_path", "")
        audio_duration = audio_info.get("duration_seconds", seg.get("duration_seconds", 5.0))

        try:
            clip = _create_segment_clip(seg, asset_info, audio_path, audio_duration)
            if clip is not None:
                clips.append(clip)
                timeline.append({
                    "segment_id": seg_id,
                    "segment_type": seg.get("segment_type", "general"),
                    "visual_type": asset_info.get("asset_type", "unknown"),
                    "start_time": round(current_time, 2),
                    "end_time": round(current_time + audio_duration, 2),
                    "duration_seconds": round(audio_duration, 2),
                })
                current_time += audio_duration

        except Exception as e:
            logger.error(f"Failed to create clip for segment {seg_id}: {e}")
            # Create a fallback black clip with audio
            fallback = _create_fallback_clip(audio_path, audio_duration)
            if fallback:
                clips.append(fallback)
                current_time += audio_duration

    if not clips:
        return {"status": "error", "error": "No clips were created. Cannot compose video."}

    # Concatenate all clips into the final video
    try:
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile(
            output_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            logger=None,  # Suppress MoviePy progress bars
        )
        final_video.close()

        # Clean up individual clips
        for clip in clips:
            clip.close()

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
            "maths_clips": sum(1 for t in timeline if t["segment_type"] == "maths"),
        }

        return {"status": "success", "video_output": json.dumps(video_result)}

    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        return {"status": "error", "error": str(e)}


def _create_segment_clip(seg, asset_info, audio_path, duration):
    """Creates a MoviePy clip for a single segment."""
    asset_type = asset_info.get("asset_type", "")

    if asset_type == "manim_video" and asset_info.get("status") == "rendered":
        video_path = asset_info.get("video_path", "")
        if video_path and os.path.exists(video_path):
            clip = VideoFileClip(video_path)
            # Resize to reel dimensions
            clip = clip.resize(height=REEL_HEIGHT)
            # Pad or crop width to match
            if clip.w != REEL_WIDTH:
                clip = clip.resize(width=REEL_WIDTH)
        else:
            clip = _create_fallback_clip(audio_path, duration)

    elif asset_type == "image" and asset_info.get("status") == "generated":
        image_path = asset_info.get("image_file_path", "")
        if image_path and os.path.exists(image_path):
            clip = ImageClip(image_path, duration=duration)
            clip = clip.resize(height=REEL_HEIGHT)
            if clip.w != REEL_WIDTH:
                clip = clip.resize(width=REEL_WIDTH)

            # Ken Burns effect: slow zoom in
            clip = clip.resize(lambda t: 1 + 0.03 * t)
            clip = clip.set_duration(duration)
        else:
            clip = _create_fallback_clip(audio_path, duration)
    else:
        clip = _create_fallback_clip(audio_path, duration)

    # Attach audio if available
    if clip and audio_path and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        # Match clip duration to audio
        if abs(clip.duration - audio.duration) > 0.5:
            clip = clip.set_duration(audio.duration)
        clip = clip.set_audio(audio)

    return clip


def _create_fallback_clip(audio_path, duration):
    """Creates a black background clip as fallback."""
    clip = ColorClip(
        size=(REEL_WIDTH, REEL_HEIGHT),
        color=(20, 20, 30),  # Near-black blue
        duration=duration,
    )
    return clip


video_editor_agent = Agent(
    name="video_editor_agent",
    model=ROUTING_MODEL,
    description=(
        "Composes the final educational reel by stitching static images "
        "and Manim video clips with synchronized TTS audio narration."
    ),
    instruction=(
        "You are the Video Editor Agent. "
        "You need three inputs from the conversation: "
        "1) The enhanced script JSON, "
        "2) The TTS output JSON, "
        "3) The QC output JSON. "
        "Call the compose_final_video tool with script_json, tts_json, "
        "and qc_output_json from the conversation context. "
        "Return ONLY the raw JSON string from the tool's 'video_output' field. "
        "Do not add any commentary."
    ),
    tools=[compose_final_video],
    output_key="video_output",
)
