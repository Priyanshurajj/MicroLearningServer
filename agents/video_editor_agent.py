import json
from google.adk.agents import Agent


def compose_final_video(script_json: str, tts_json: str, qc_assets_json: str) -> dict:
    """
    Composes the final educational reel video by stitching together:
    - Static images (for general segments) with Ken Burns effects
    - Manim .mp4 clips (for maths segments)
    - TTS audio narration synchronized to each segment
    All segments are ordered by segment_id and crossfaded.
    In production, uses MoviePy/FFmpeg for actual composition.
    """
    try:
        script = json.loads(script_json)
        tts_data = json.loads(tts_json)
        qc_data = json.loads(qc_assets_json)
    except json.JSONDecodeError:
        return {"status": "error", "error_message": "Invalid JSON provided to Video Editor."}

    segments = script.get("segments", [])
    audio_segments = {s["segment_id"]: s for s in tts_data.get("audio_segments", [])}
    qc_assets = {a["segment_id"]: a for a in qc_data.get("qc_assets", [])}

    timeline = []
    current_time = 0.0

    for seg in sorted(segments, key=lambda s: s["segment_id"]):
        seg_id = seg["segment_id"]
        duration = seg.get("duration_seconds", 5.0)
        audio = audio_segments.get(seg_id, {})
        asset = qc_assets.get(seg_id, {})

        clip_info = {
            "segment_id": seg_id,
            "segment_type": seg.get("segment_type", "general"),
            "start_time": current_time,
            "end_time": current_time + duration,
            "duration_seconds": duration,
            "audio_path": audio.get("audio_file_path", f"/tmp/audio/segment_{seg_id}.mp3"),
        }

        if asset.get("asset_type") == "manim_video":
            clip_info["visual_type"] = "video_clip"
            clip_info["visual_path"] = asset.get("video_path", f"/tmp/manim/segment_{seg_id}.mp4")
            clip_info["effects"] = ["overlay_audio", "crossfade_in"]
        else:
            clip_info["visual_type"] = "static_image"
            clip_info["visual_path"] = asset.get("image_file_path", f"/tmp/images/segment_{seg_id}.png")
            clip_info["effects"] = ["ken_burns_zoom", "crossfade_transition", "text_overlay"]

        timeline.append(clip_info)
        current_time += duration

    video_result = {
        "video_file_path": "/tmp/videos/final_reel.mp4",
        "duration_seconds": current_time,
        "resolution": "1080x1920",
        "format": "mp4",
        "fps": 30,
        "timeline": timeline,
        "total_clips": len(timeline),
        "general_clips": sum(1 for c in timeline if c["segment_type"] == "general"),
        "maths_clips": sum(1 for c in timeline if c["segment_type"] == "maths"),
        "effects_applied": [
            "ken_burns_zoom",
            "crossfade_transitions",
            "manim_clip_integration",
            "tts_audio_sync",
            "background_music",
        ],
    }

    return {"status": "success", "video_output": json.dumps(video_result)}


video_editor_agent = Agent(
    name="video_editor_agent",
    model="gemini-3-flash-preview",
    description=(
        "Final video composition agent — stitches together static images and Manim "
        "video clips with TTS audio, applying Ken Burns effects and crossfade transitions "
        "to produce the final mixed-content educational reel."
    ),
    instruction=(
        "You are the Video Editor Agent. You receive: "
        "the enhanced script from 'enhanced_script', "
        "TTS audio data from 'tts_output', "
        "and QC'd visual assets from 'qc_output' in the session state. "
        "Use the compose_final_video tool with script_json, tts_json, and qc_assets_json. "
        "Return ONLY the raw JSON string from the tool's 'video_output' field. "
        "Do not add any extra commentary."
    ),
    tools=[compose_final_video],
    output_key="video_output",
)
