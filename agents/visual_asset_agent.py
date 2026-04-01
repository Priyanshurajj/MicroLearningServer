import json
import os
import io
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai
from PIL import Image

from .config import get_client, CODE_MODEL, IMAGEN_MODEL, ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")

MANIM_CODE_PROMPT = """You are an expert Manim Community Edition (manim) Python developer.
Generate a complete, self-contained Manim script for the following educational animation.

REQUIREMENTS:
- Import everything from manim: `from manim import *`
- Create exactly ONE Scene class named `Segment{segment_id}Scene`
- Use a DARK background (default Manim)
- Use MathTex for LaTeX math expressions, Tex for regular text
- Include smooth animations: Write, FadeIn, FadeOut, Transform, Create
- Add self.wait() calls between animations for pacing
- Target duration: approximately {duration} seconds
- Use vibrant colors: BLUE, YELLOW, GREEN, RED, WHITE for text
- For geometry: use Circle, Square, Line, Arrow, Polygon, etc.
- For graphs: use Axes, NumberPlane if applicable
- End with self.wait(1) to hold the final frame
- Code must be error-free and executable with `manim render -ql`
- DO NOT use any external files or images
- DO NOT use deprecated Manim API calls

SEGMENT DETAILS:
- Narration: {narration}
- Visual Description: {visual_description}
- Math Expression: {math_expression}
{manim_spec}

Return ONLY the Python code. No explanations, no markdown code blocks.
"""


def generate_visual_assets(tool_context: ToolContext) -> dict:
    """Reads enhanced_script from session state and generates visuals."""
    script_json = tool_context.state.get("enhanced_script", "")
    if not script_json:
        script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Visual assets: Cannot parse script from state: {e}")
        return {"status": "error", "error": f"Cannot parse script from state: {e}"}

    run_id = script.get("run_id", "default")
    images_dir = os.path.join(OUTPUT_DIR, run_id, "images")
    manim_dir = os.path.join(OUTPUT_DIR, run_id, "manim")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(manim_dir, exist_ok=True)

    segments = script.get("segments", [])
    visual_assets = []

    for seg in segments:
        seg_id = seg["segment_id"]
        seg_type = seg.get("segment_type", "general")

        if seg_type == "manim":
            asset = _generate_manim_code(seg, manim_dir)
        else:
            asset = _generate_image(seg, images_dir)

        visual_assets.append(asset)

    result = {
        "run_id": run_id,
        "visual_assets": visual_assets,
        "total_assets": len(visual_assets),
        "manim_clips": sum(1 for a in visual_assets if a["asset_type"] == "manim_code"),
        "general_images": sum(1 for a in visual_assets if a["asset_type"] == "image"),
    }

    logger.info(
        f"Visual assets: {result['general_images']} images, "
        f"{result['manim_clips']} Manim scripts generated"
    )

    visual_output_json = json.dumps(result)
    tool_context.state["visual_output"] = visual_output_json
    return {"status": "success", "visual_output": visual_output_json}


def _generate_image(seg: dict, images_dir: str) -> dict:
    seg_id = seg["segment_id"]
    output_path = os.path.join(images_dir, f"segment_{seg_id}.png")

    prompt = seg.get("image_prompt",
                seg.get("enhanced_visual",
                    seg.get("visual_description", "Educational illustration")))

    prompt = prompt[:1000]

    try:
        response = get_client().models.generate_images(
            model=IMAGEN_MODEL,
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
            ),
        )

        if response.generated_images:
            image_data = response.generated_images[0].image
            pil_image = Image.open(io.BytesIO(image_data.image_bytes))
            pil_image.save(output_path, "PNG")

            logger.info(f"Image generated for segment {seg_id}")

            return {
                "segment_id": seg_id,
                "asset_type": "image",
                "image_file_path": os.path.abspath(output_path),
                "prompt_used": prompt[:200],
                "status": "generated",
            }
        else:
            logger.warning(f"Imagen returned no images for segment {seg_id}")
            return {
                "segment_id": seg_id,
                "asset_type": "image",
                "image_file_path": "",
                "status": "failed",
                "error": "Imagen returned no images",
            }

    except Exception as e:
        logger.error(f"Image generation failed for segment {seg_id}: {e}")
        return {
            "segment_id": seg_id,
            "asset_type": "image",
            "image_file_path": "",
            "status": "failed",
            "error": str(e),
        }


def _generate_manim_code(seg: dict, manim_dir: str) -> dict:
    seg_id = seg["segment_id"]
    code_path = os.path.join(manim_dir, f"segment_{seg_id}.py")

    manim_spec_str = ""
    if "manim_spec" in seg:
        manim_spec_str = f"- Manim Specification: {json.dumps(seg['manim_spec'], indent=2)}"

    prompt = MANIM_CODE_PROMPT.format(
        segment_id=seg_id,
        duration=seg.get("duration_seconds", 5),
        narration=seg.get("narration", ""),
        visual_description=seg.get("visual_description", ""),
        math_expression=seg.get("math_expression", ""),
        manim_spec=manim_spec_str,
    )

    try:
        response = get_client().models.generate_content(
            model=CODE_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.2,
            ),
        )

        code = response.text.strip()

        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)

        logger.info(f"Manim code generated for segment {seg_id}")

        return {
            "segment_id": seg_id,
            "asset_type": "manim_code",
            "code_file_path": os.path.abspath(code_path),
            "scene_name": f"Segment{seg_id}Scene",
            "output_video_path": os.path.abspath(
                os.path.join(manim_dir, f"segment_{seg_id}.mp4")
            ),
            "status": "code_generated",
        }

    except Exception as e:
        logger.error(f"Manim code generation failed for segment {seg_id}: {e}")
        return {
            "segment_id": seg_id,
            "asset_type": "manim_code",
            "code_file_path": "",
            "status": "failed",
            "error": str(e),
        }


visual_asset_agent = Agent(
    name="visual_asset_agent",
    model=ROUTING_MODEL,
    description=(
        "Generates visual assets: Imagen images for general segments "
        "and Gemini 2.5 Pro Manim Python code for manim segments."
    ),
    instruction=(
        "You are the Visual Asset Agent. "
        "Call the generate_visual_assets tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_visual_assets],
)
