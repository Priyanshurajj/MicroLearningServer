import json
from google.adk.agents import Agent

def compose_video(tts_json: str, images_json: str) -> dict:
    try:
        tts_data = json.loads(tts_json)
        image_data = json.loads(images_json)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Invalid JSON provided to Video Generation agent.",
        }

    total_duration = tts_data.get("total_duration_seconds", 25.0)
    num_segments = len(image_data.get("images", []))

    video_result = {
        "video_file_path": "/tmp/videos/final_reel_general.mp4",
        "duration_seconds": total_duration,
        "resolution": "1080x1920",
        "format": "mp4",
        "pipeline_used": "general",
        "segments_composed": num_segments,
        "effects_applied": [
            "ken_burns_zoom",
            "crossfade_transitions",
            "background_music",
            "text_overlays",
        ],
    }

    return {"status": "success", "video_output": json.dumps(video_result)}

video_generation_agent = Agent(
    name="video_generation_agent",
    model="gemini-3-flash-preview",
    description=(
        "Composes a final documentary-style educational reel video by combining "
        "TTS audio narration with generated images using cinematic effects."
    ),
    instruction=(
        "You are a Video Generation Agent for GENERAL educational content. "
        "You receive TTS audio data from 'tts_output' and image data from "
        "'image_output' in the session state. "
        "Use the compose_video tool with the tts_json and images_json arguments "
        "from the conversation context. "
        "Return ONLY the raw JSON string from the tool's 'video_output' field. "
        "Do not add any extra commentary."
    ),
    tools=[compose_video],
    output_key="video_output",
)
