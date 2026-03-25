import json
from google.adk.agents import Agent

def generate_images(script_json: str) -> dict:
    try:
        script = json.loads(script_json)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Invalid script JSON provided to Image Generation agent.",
        }

    segments = script.get("segments", [])
    images = []

    for seg in segments:
        visual_desc = seg.get("visual_description", "Educational illustration")
        images.append({
            "segment_id": seg["segment_id"],
            "image_file_path": f"/tmp/images/segment_{seg['segment_id']}.png",
            "image_prompt_used": f"Educational reel illustration: {visual_desc}",
        })

    image_result = {"images": images}

    return {"status": "success", "image_output": json.dumps(image_result)}


IMAGE_INSTRUCTION = (
    "You are an Image Generation Agent. You receive a script from the session "
    "state under 'script_output'. Use the generate_images tool with the script "
    "JSON to produce images for each segment. "
    "Pass the value of 'script_output' from the conversation context as the "
    "script_json argument. "
    "Return ONLY the raw JSON string from the tool's 'image_output' field. "
    "Do not add any extra commentary."
)

IMAGE_DESCRIPTION = (
    "Generates visual images for each segment of the educational script "
    "based on the visual descriptions provided."
)

image_agent_general = Agent(
    name="image_agent_general",
    model="gemini-3-flash-preview",
    description=IMAGE_DESCRIPTION,
    instruction=IMAGE_INSTRUCTION,
    tools=[generate_images],
    output_key="image_output",
)

image_agent_maths = Agent(
    name="image_agent_maths",
    model="gemini-3-flash-preview",
    description=IMAGE_DESCRIPTION,
    instruction=IMAGE_INSTRUCTION,
    tools=[generate_images],
    output_key="image_output",
)
