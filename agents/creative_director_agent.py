import json
from google.adk.agents import Agent


def enhance_visual_prompts(script_json: str) -> dict:
    try:
        script = json.loads(script_json)
    except json.JSONDecodeError:
        return {"status": "error", "error_message": "Invalid JSON provided to Creative Director."}

    enhanced_segments = []
    for seg in script.get("segments", []):
        enhanced = {**seg}

        if seg.get("segment_type") == "maths":
            math_expr = seg.get("math_expression", "")
            enhanced["manim_spec"] = {
                "scene_type": "equation_animation",
                "expression": math_expr,
                "animation_style": "write_then_transform",
                "color_scheme": "dark_background_white_text",
                "description": f"Animate the expression: {math_expr}. "
                               f"Show step-by-step derivation with smooth transitions.",
            }
            enhanced["enhanced_visual"] = (
                f"Manim animation: {seg['visual_description']}. "
                f"Use dark background with vibrant equation colors. "
                f"Include geometric shapes if applicable."
            )
        else:
            enhanced["enhanced_visual"] = (
                f"Cinematic 4K illustration, documentary style, "
                f"soft lighting, educational infographic aesthetic: "
                f"{seg['visual_description']}. "
                f"Color palette: warm earth tones with accent highlights. "
                f"Include subtle depth-of-field blur on background elements."
            )
            enhanced["image_prompt"] = (
                f"A high-quality educational illustration showing: "
                f"{seg['visual_description']}. "
                f"Style: modern flat design with subtle 3D elements, "
                f"warm color palette, clean typography, "
                f"aspect ratio 9:16 for mobile reel."
            )

        enhanced_segments.append(enhanced)

    enhanced_script = {**script, "segments": enhanced_segments}
    return {"status": "success", "enhanced_script": json.dumps(enhanced_script)}


creative_director_agent = Agent(
    name="creative_director_agent",
    model="gemini-3-flash-preview",
    description=(
        "Enhances script segment visual descriptions into production-grade prompts: "
        "cinematic image prompts for general segments and Manim code specs for maths segments."
    ),
    instruction=(
        "You are the Creative Director Agent. You receive a script from 'script_output' "
        "in the session state. Use the enhance_visual_prompts tool, passing the script JSON. "
        "Return ONLY the raw JSON string from the tool's 'enhanced_script' field. "
        "Do not add any extra commentary."
    ),
    tools=[enhance_visual_prompts],
    output_key="enhanced_script",
)
