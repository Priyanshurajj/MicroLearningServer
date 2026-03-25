import json
from google.adk.agents import Agent

def compose_manim_video(script_json: str, tts_json: str, images_json: str) -> dict:
    try:
        script_data = json.loads(script_json)
        tts_data = json.loads(tts_json)
        image_data = json.loads(images_json)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Invalid JSON provided to Manim Video Generation agent.",
        }

    total_duration = tts_data.get("total_duration_seconds", 25.0)
    num_segments = len(script_data.get("segments", []))

    video_result = {
        "video_file_path": "/tmp/videos/final_reel_manim.mp4",
        "duration_seconds": total_duration,
        "resolution": "1080x1920",
        "format": "mp4",
        "pipeline_used": "maths",
        "segments_composed": num_segments,
        "manim_scenes_generated": num_segments,
        "effects_applied": [
            "manim_equation_animations",
            "geometric_visualizations",
            "graph_plotting",
            "step_by_step_derivations",
            "tts_sync",
        ],
    }

    return {"status": "success", "video_output": json.dumps(video_result)}


manim_video_generation_agent = Agent(
    name="manim_video_generation_agent",
    model="gemini-3-flash-preview",
    description=(
        "Composes a final educational reel video using Manim animations for "
        "mathematical content - renders animated equations, geometric "
        "visualizations, and graph animations synchronized with TTS narration."
    ),
    instruction=(
        "You are a Manim Video Generation Agent for MATHEMATICAL educational content. "
        "You receive script data from 'script_output', TTS audio data from 'tts_output', "
        "and image data from 'image_output' in the session state. "
        "Use the compose_manim_video tool with script_json, tts_json, and images_json "
        "from the conversation context. "
        "Return ONLY the raw JSON string from the tool's 'video_output' field. "
        "Do not add any extra commentary."
    ),
    tools=[compose_manim_video],
    output_key="video_output",
)
