import json
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai
from .config import get_client, TEXT_MODEL, ROUTING_MODEL

logger = logging.getLogger("EduReelADK")

CREATIVE_ENHANCEMENT_PROMPT = """You are a Creative Director for an educational video production studio specializing in cinematic, high-quality short-form reels.

You will receive a structured video script with segments. Your job is to enhance each segment's visual description into a production-grade specification.

FOR "general" SEGMENTS:
- Rewrite the visual_description into a detailed, cinematic image generation prompt
- Art style: STRICTLY photorealistic and cinematic. No illustrations, no flat design, no cartoons, no vector art, no anime.
- Shot style: Cinematic wide shot or extreme close-up. Shot on RED camera. 8K ultra-detailed. Shallow depth of field.
- Lighting: Dramatic (chiaroscuro, golden hour, or professional studio lighting with deep shadows).
- Mood: BBC/National Geographic documentary quality — awe-inspiring, visceral, emotionally engaging.
- Quality: ultra-detailed, professional color grading, film grain, photojournalistic.
- No text overlays, watermarks, borders, or frames in the image.
- Add an "image_prompt" field with the full Imagen-ready prompt.
- Target aspect ratio: 9:16 (vertical reel)

FOR "maths" SEGMENTS:
- Design a detailed Manim animation specification
- Add a "manim_spec" field with:
  - "scene_description": what the viewer should see
  - "animations": list of animation steps (Write equations, Transform between equations, FadeIn, etc.)
  - "color_scheme": specific Manim color constants to use
  - "math_elements": list of MathTex/Tex items to create, covering ALL math_expressions in order
- Set "background_image" to true if a real-world cinematic background would enhance comprehension
  (e.g. gravity equation → space/planet photo, photosynthesis → sunlit forest).
  Set to false for purely abstract concepts (algebra manipulation, pure geometry, etc.).
- When background_image is true, also add an "image_prompt" describing a dramatic, blurred
  real-world scene relevant to the concept (it will be shown defocused behind the animation).

FOR ALL SEGMENTS — OPTIONAL text overlay:
- Add a "text_overlay" field ONLY IF the segment introduces a named concept, formula title, or
  key term that a viewer would benefit from seeing written on screen.
- Leave "text_overlay" COMPLETELY ABSENT for narrative, transitional, or hook segments.
- When added: 1-2 lines maximum, only 1-3 highlight_words (the single most important term).
  Format: {{"lines": ["Term Name"], "highlight_words": ["Term"]}}

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

        enhanced_script_json = json.dumps(enhanced_script)
        tool_context.state["enhanced_script"] = enhanced_script_json
        return {"status": "success", "enhanced_script": enhanced_script_json}

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
)
