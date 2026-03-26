import json
from google.adk.agents import Agent


def generate_visual_assets(script_json: str) -> dict:
    """
    Generates visual assets for ALL segments concurrently.
    For 'general' segments: generates images using the enhanced image prompts.
    For 'maths' segments: generates Manim Python code from the manim_spec.
    In production, this would use asyncio.gather() for parallel API calls.
    """
    try:
        script = json.loads(script_json)
    except json.JSONDecodeError:
        return {"status": "error", "error_message": "Invalid JSON provided to Visual Asset agent."}

    segments = script.get("segments", [])
    visual_assets = []

    for seg in segments:
        seg_id = seg["segment_id"]
        seg_type = seg.get("segment_type", "general")

        if seg_type == "maths":
            manim_spec = seg.get("manim_spec", {})
            expression = manim_spec.get("expression", "x^2")
            visual_assets.append({
                "segment_id": seg_id,
                "asset_type": "manim_code",
                "manim_code": (
                    f"from manim import *\n\n"
                    f"class Segment{seg_id}Scene(Scene):\n"
                    f"    def construct(self):\n"
                    f"        eq = MathTex(r\"{expression}\")\n"
                    f"        self.play(Write(eq))\n"
                    f"        self.wait(2)\n"
                ),
                "output_path": f"/tmp/manim/segment_{seg_id}.mp4",
                "status": "code_generated",
            })
        else:
            prompt = seg.get("image_prompt", seg.get("enhanced_visual", seg.get("visual_description", "")))
            visual_assets.append({
                "segment_id": seg_id,
                "asset_type": "image",
                "image_file_path": f"/tmp/images/segment_{seg_id}.png",
                "prompt_used": prompt[:200],
                "status": "generated",
            })

    result = {
        "visual_assets": visual_assets,
        "total_assets": len(visual_assets),
        "maths_clips": sum(1 for a in visual_assets if a["asset_type"] == "manim_code"),
        "general_images": sum(1 for a in visual_assets if a["asset_type"] == "image"),
    }

    return {"status": "success", "visual_output": json.dumps(result)}


visual_asset_agent = Agent(
    name="visual_asset_agent",
    model="gemini-3-flash-preview",
    description=(
        "Generates visual assets for all segments: images for general segments "
        "and Manim Python code for maths segments."
    ),
    instruction=(
        "You are the Visual Asset Agent. You receive an enhanced script from 'enhanced_script' "
        "in the session state. Use the generate_visual_assets tool, passing the script JSON. "
        "Return ONLY the raw JSON string from the tool's 'visual_output' field. "
        "Do not add any extra commentary."
    ),
    tools=[generate_visual_assets],
    output_key="visual_output",
)
