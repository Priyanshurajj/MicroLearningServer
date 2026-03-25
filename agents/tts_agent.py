import json
from google.adk.agents import Agent

def generate_tts(script_json: str) -> dict:
    try:
        script = json.loads(script_json)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Invalid script JSON provided to TTS agent.",
        }

    segments = script.get("segments", [])
    audio_segments = []

    for seg in segments:
        audio_segments.append({
            "segment_id": seg["segment_id"],
            "audio_file_path": f"/tmp/audio/segment_{seg['segment_id']}.mp3",
            "duration_seconds": seg.get("duration_seconds", 5.0),
        })

    tts_result = {
        "audio_segments": audio_segments,
        "total_duration_seconds": sum(
            s["duration_seconds"] for s in audio_segments
        ),
    }

    return {"status": "success", "tts_output": json.dumps(tts_result)}


TTS_INSTRUCTION = (
    "You are a TTS (Text-to-Speech) Agent. You receive a script from the "
    "previous step stored in the session state under 'script_output'. "
    "Use the generate_tts tool with the script JSON to produce audio files. "
    "Pass the value of 'script_output' from the conversation context as the "
    "script_json argument. "
    "Return ONLY the raw JSON string from the tool's 'tts_output' field. "
    "Do not add any extra commentary."
)

TTS_DESCRIPTION = (
    "Generates text-to-speech audio narration for each segment of the "
    "educational script."
)

tts_agent_general = Agent(
    name="tts_agent_general",
    model="gemini-3-flash-preview",
    description=TTS_DESCRIPTION,
    instruction=TTS_INSTRUCTION,
    tools=[generate_tts],
    output_key="tts_output",
)

tts_agent_maths = Agent(
    name="tts_agent_maths",
    model="gemini-3-flash-preview",
    description=TTS_DESCRIPTION,
    instruction=TTS_INSTRUCTION,
    tools=[generate_tts],
    output_key="tts_output",
)
