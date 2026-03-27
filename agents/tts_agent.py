import json
import os
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from gtts import gTTS
from moviepy import AudioFileClip

from .config import ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")


def generate_tts_audio(tool_context: ToolContext) -> dict:
    """Reads enhanced_script from session state and generates TTS audio for all segments."""
    script_json = tool_context.state.get("enhanced_script", "")
    if not script_json:
        script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"TTS: Cannot parse script from state: {e}")
        return {"status": "error", "error": f"Cannot parse script from state: {e}"}

    run_id = script.get("run_id", "default")
    audio_dir = os.path.join(OUTPUT_DIR, run_id, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    segments = script.get("segments", [])
    audio_segments = []

    for seg in segments:
        seg_id = seg["segment_id"]
        narration = seg.get("narration", "")
        output_path = os.path.join(audio_dir, f"segment_{seg_id}.mp3")

        try:
            tts = gTTS(text=narration, lang="en", slow=False)
            tts.save(output_path)

            audio_clip = AudioFileClip(output_path)
            actual_duration = audio_clip.duration
            audio_clip.close()

            audio_segments.append({
                "segment_id": seg_id,
                "audio_file_path": os.path.abspath(output_path),
                "duration_seconds": round(actual_duration, 2),
                "narration_preview": narration[:80],
            })

            logger.info(f"TTS segment {seg_id}: {actual_duration:.1f}s")

        except Exception as e:
            logger.error(f"TTS failed for segment {seg_id}: {e}")
            audio_segments.append({
                "segment_id": seg_id,
                "audio_file_path": "",
                "duration_seconds": seg.get("duration_seconds", 5.0),
                "error": str(e),
            })

    tts_result = {
        "run_id": run_id,
        "audio_segments": audio_segments,
        "total_duration_seconds": round(
            sum(s["duration_seconds"] for s in audio_segments), 2
        ),
        "segments_processed": len(audio_segments),
    }

    logger.info(
        f"TTS complete: {len(audio_segments)} segments, "
        f"total {tts_result['total_duration_seconds']}s"
    )

    return {"status": "success", "tts_output": json.dumps(tts_result)}


tts_agent = Agent(
    name="tts_agent",
    model=ROUTING_MODEL,
    description="Generates text-to-speech audio narration for all segments.",
    instruction=(
        "You are the TTS Agent. "
        "Call the generate_tts_audio tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_tts_audio],
    output_key="tts_output",
)
