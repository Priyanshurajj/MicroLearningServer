import json
from google.adk.agents import Agent


def generate_tts(script_json: str) -> dict:
    """
    Generates TTS audio files for ALL segments of the script concurrently.
    In production, this would use asyncio.gather() to hit the TTS API in parallel.
    """
    try:
        script = json.loads(script_json)
    except json.JSONDecodeError:
        return {"status": "error", "error_message": "Invalid script JSON provided to TTS agent."}

    segments = script.get("segments", [])
    audio_segments = []

    for seg in segments:
        audio_segments.append({
            "segment_id": seg["segment_id"],
            "audio_file_path": f"/tmp/audio/segment_{seg['segment_id']}.mp3",
            "duration_seconds": seg.get("duration_seconds", 5.0),
            "narration_preview": seg.get("narration", "")[:60],
        })

    tts_result = {
        "audio_segments": audio_segments,
        "total_duration_seconds": sum(s["duration_seconds"] for s in audio_segments),
        "segments_processed": len(audio_segments),
    }

    return {"status": "success", "tts_output": json.dumps(tts_result)}


tts_agent = Agent(
    name="tts_agent",
    model="gemini-3-flash-preview",
    description="Generates text-to-speech audio narration for all segments of the educational script.",
    instruction=(
        "You are the TTS Agent. You receive an enhanced script from 'enhanced_script' "
        "in the session state. Use the generate_tts tool, passing the script JSON. "
        "Return ONLY the raw JSON string from the tool's 'tts_output' field. "
        "Do not add any extra commentary."
    ),
    tools=[generate_tts],
    output_key="tts_output",
)
