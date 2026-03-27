import json
import os
import logging
import subprocess
import tempfile

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from moviepy import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    ColorClip,
)
import imageio_ffmpeg

from .config import ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")

REEL_WIDTH = 1080
REEL_HEIGHT = 1920
FPS = 30


def compose_final_video(tool_context: ToolContext) -> dict:
    """Reads enhanced_script, tts_output, qc_output from session state."""
    try:
        script = json.loads(tool_context.state.get("enhanced_script", "{}"))
        tts_data = json.loads(tool_context.state.get("tts_output", "{}"))
        qc_data = json.loads(tool_context.state.get("qc_output", "{}"))
    except (json.JSONDecodeError, TypeError) as e:
        return {"status": "error", "error": f"Invalid JSON provided to Video Editor: {e}"}

    run_id = script.get("run_id", qc_data.get("run_id", "default"))
    output_path = os.path.join(OUTPUT_DIR, run_id, "final_reel.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    segments = sorted(script.get("segments", []), key=lambda s: s["segment_id"])

    # Normalize paths that may have been double-escaped through JSON layers
    audio_map = {}
    for s in tts_data.get("audio_segments", []):
        s["audio_file_path"] = os.path.normpath(s.get("audio_file_path", ""))
        audio_map[s["segment_id"]] = s

    asset_map = {}
    for a in qc_data.get("qc_assets", []):
        for key in ("image_file_path", "video_path"):
            if key in a:
                a[key] = os.path.normpath(a[key])
        asset_map[a["segment_id"]] = a

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
            fallback = _create_fallback_clip(audio_path, audio_duration)
            if fallback:
                clips.append(fallback)
                current_time += audio_duration

    if not clips:
        return {"status": "error", "error": "No clips were created."}

    # ── Write video using subprocess FFmpeg (avoids pipe deadlock) ──
    try:
        final_video = concatenate_videoclips(clips, method="compose")

        # Step 1: Write a temporary raw video (no audio) using imageio
        # This avoids the FFmpeg pipe deadlock that write_videofile causes
        temp_video = os.path.join(os.path.dirname(output_path), "temp_video.mp4")
        temp_audio = os.path.join(os.path.dirname(output_path), "temp_audio.mp3")

        # Write video without audio first — uses imageio internally, no pipe issues
        final_video.without_audio().write_videofile(
            temp_video,
            fps=FPS,
            codec="libx264",
            logger="bar",  # MUST keep "bar" — None causes FFmpeg pipe deadlock
        )

        # Write concatenated audio separately
        if final_video.audio is not None:
            final_video.audio.write_audiofile(temp_audio, logger="bar")

        final_video.close()
        for clip in clips:
            clip.close()

        # Step 2: Merge video + audio with FFmpeg subprocess (non-blocking, clean pipes)
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
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Cleanup temp files
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
            "maths_clips": sum(1 for t in timeline if t["segment_type"] == "maths"),
        }

        video_output_json = json.dumps(video_result)
        tool_context.state["video_output"] = video_output_json
        return {"status": "success", "video_output": video_output_json}

    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        return {"status": "error", "error": str(e)}


def _create_segment_clip(seg, asset_info, audio_path, duration):
    asset_type = asset_info.get("asset_type", "")

    if asset_type == "manim_video" and asset_info.get("status") == "rendered":
        video_path = asset_info.get("video_path", "")
        if video_path and os.path.exists(video_path):
            clip = VideoFileClip(video_path)
            clip = clip.resized(height=REEL_HEIGHT)
            if clip.w != REEL_WIDTH:
                clip = clip.resized(width=REEL_WIDTH)
        else:
            clip = _create_fallback_clip(audio_path, duration)

    elif asset_type == "image" and asset_info.get("status") == "generated":
        image_path = asset_info.get("image_file_path", "")
        if image_path and os.path.exists(image_path):
            clip = ImageClip(image_path, duration=duration)
            clip = clip.resized(height=REEL_HEIGHT)
            if clip.w != REEL_WIDTH:
                clip = clip.resized(width=REEL_WIDTH)

            # Ken Burns effect: slow zoom in
            clip = clip.resized(lambda t: 1 + 0.03 * t)
            clip = clip.with_duration(duration)
        else:
            clip = _create_fallback_clip(audio_path, duration)
    else:
        clip = _create_fallback_clip(audio_path, duration)

    # Attach audio
    if clip and audio_path and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        if abs(clip.duration - audio.duration) > 0.5:
            clip = clip.with_duration(audio.duration)
        clip = clip.with_audio(audio)

    return clip


def _create_fallback_clip(audio_path, duration):
    clip = ColorClip(
        size=(REEL_WIDTH, REEL_HEIGHT),
        color=(20, 20, 30),
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
        "Call the compose_final_video tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[compose_final_video],
)

