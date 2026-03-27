import json
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai
from .config import get_client, TEXT_MODEL, ROUTING_MODEL

logger = logging.getLogger("EduReelADK")

CREATIVE_ENHANCEMENT_PROMPT = """You are a Creative Director for an educational video production studio.

You will receive a structured video script with segments. Your job is to enhance each segment's visual description into a production-grade prompt.

FOR "general" SEGMENTS:
- Rewrite the visual_description into a detailed, cinematic image generation prompt
- Include: art style (modern flat design / 3D render / photorealistic), color palette, composition, lighting, mood
- Add an "image_prompt" field with the full Imagen-ready prompt
- Target aspect ratio: 9:16 (vertical reel)
- The image should be educational, clean, and visually stunning

FOR "maths" SEGMENTS:
- Design a detailed Manim animation specification
- Add a "manim_spec" field with:
  - "scene_description": what the viewer should see
  - "animations": list of animation steps (Write equations, Transform, FadeIn, etc.)
  - "color_scheme": specific Manim color constants to use
  - "math_elements": list of MathTex/Tex items to create
- The specification should be detailed enough for code generation

INPUT SCRIPT:
{script_json}

OUTPUT FORMAT (strict JSON — same structure as input, with added fields):
Return the FULL script JSON with the original fields preserved and the new enhancement fields added to each segment.
"""


def enhance_visual_prompts(tool_context: ToolContext) -> dict:
    """Reads script_output from session state and enhances visual prompts."""
    script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)

        prompt = CREATIVE_ENHANCEMENT_PROMPT.format(script_json=script_json)

        response = get_client().models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.8,
            ),
        )

        enhanced_script = json.loads(response.text)

        if "run_id" in script and "run_id" not in enhanced_script:
            enhanced_script["run_id"] = script["run_id"]

        general_count = sum(
            1 for s in enhanced_script.get("segments", [])
            if s.get("segment_type") == "general"
        )
        maths_count = sum(
            1 for s in enhanced_script.get("segments", [])
            if s.get("segment_type") == "maths"
        )
        logger.info(
            f"Creative enhancement complete: {general_count} general, {maths_count} maths segments"
        )

        return {"status": "success", "enhanced_script": json.dumps(enhanced_script)}

    except json.JSONDecodeError as e:
        logger.error(f"Creative Director received invalid JSON: {e}")
        return {"status": "error", "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        logger.error(f"Creative enhancement failed: {e}")
        return {"status": "error", "error": str(e)}


creative_director_agent = Agent(
    name="creative_director_agent",
    model=ROUTING_MODEL,
    description=(
        "Enhances script visual descriptions into production-grade image prompts "
        "for Imagen and Manim animation specifications."
    ),
    instruction=(
        "You are the Creative Director Agent. "
        "Call the enhance_visual_prompts tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[enhance_visual_prompts],
    output_key="enhanced_script",
)
