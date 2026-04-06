import json
import os
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai
from PIL import Image

from .config import get_client, IMAGEN_MODEL, ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")


def generate_manim_bg_images(tool_context: ToolContext) -> dict:
    """Generates blurred background images for manim segments that have background_image: true.

    Runs inside manim_pipeline (after creative_director, before manim_qc_agent),
    keeping the manim pipeline fully self-contained. Writes to bg_image_output.
    """
    script_json = tool_context.state.get("enhanced_script", "")
    if not script_json:
        script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Manim BG Image Agent: Cannot parse script from state: {e}")
        return {"status": "error", "error": f"Cannot parse script from state: {e}"}

    run_id = script.get("run_id", "default")
    # Store background images alongside regular images but with a bg_ prefix
    images_dir = os.path.join(OUTPUT_DIR, run_id, "images")
    os.makedirs(images_dir, exist_ok=True)

    bg_segments = [
        seg for seg in script.get("segments", [])
        if seg.get("segment_type") == "manim" and seg.get("background_image", False)
    ]

    if not bg_segments:
        result = {"run_id": run_id, "bg_images": [], "total_bg_images": 0}
        tool_context.state["bg_image_output"] = json.dumps(result)
        return {"status": "success", "bg_image_output": json.dumps(result)}

    bg_images = []

    with ThreadPoolExecutor(max_workers=min(len(bg_segments), 4)) as executor:
        futures = {
            executor.submit(_generate_single_bg_image, seg, images_dir): seg
            for seg in bg_segments
        }
        for future in as_completed(futures):
            bg_images.append(future.result())

    bg_images.sort(key=lambda x: x["segment_id"])

    result = {
        "run_id": run_id,
        "bg_images": bg_images,
        "total_bg_images": len(bg_images),
        "generated": sum(1 for i in bg_images if i["status"] == "generated"),
        "failed": sum(1 for i in bg_images if i["status"] == "failed"),
    }

    logger.info(
        f"Manim BG Image Agent: {result['generated']} background images generated, "
        f"{result['failed']} failed"
    )

    bg_output_json = json.dumps(result)
    tool_context.state["bg_image_output"] = bg_output_json
    return {"status": "success", "bg_image_output": bg_output_json}


def _generate_single_bg_image(seg: dict, images_dir: str) -> dict:
    """Generates one blurred/moody background image for a manim segment."""
    seg_id = seg["segment_id"]
    output_path = os.path.join(images_dir, f"bg_segment_{seg_id}.png")

    # Prefer the image_prompt added by creative_director for bg-enabled manim segments
    prompt = seg.get(
        "image_prompt",
        seg.get("visual_description", "Abstract educational background"),
    )
    # Append background-specific qualifiers
    prompt = (
        prompt[:880]
        + " Cinematic background, no text, no UI elements, no people. "
        "Soft bokeh, slightly defocused, dark atmospheric mood, suitable as a "
        "blurred video background behind animated equations."
    )
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
            pil_image = Image.open(
                io.BytesIO(response.generated_images[0].image.image_bytes)
            )
            pil_image.save(output_path, "PNG")
            logger.info(f"Background image generated for manim segment {seg_id}")
            return {
                "segment_id": seg_id,
                "asset_type": "bg_image",
                "image_file_path": os.path.abspath(output_path),
                "prompt_used": prompt[:200],
                "status": "generated",
            }
        else:
            logger.warning(f"Imagen returned no bg image for segment {seg_id}")
            return {
                "segment_id": seg_id,
                "asset_type": "bg_image",
                "image_file_path": "",
                "status": "failed",
                "error": "Imagen returned no images",
            }

    except Exception as e:
        logger.error(f"BG image generation failed for segment {seg_id}: {e}")
        return {
            "segment_id": seg_id,
            "asset_type": "bg_image",
            "image_file_path": "",
            "status": "failed",
            "error": str(e),
        }


manim_bg_image_agent = Agent(
    name="manim_bg_image_agent",
    model=ROUTING_MODEL,
    description=(
        "Generates blurred cinematic background images for manim segments with "
        "background_image: true. Part of manim_pipeline. Writes to bg_image_output."
    ),
    instruction=(
        "You are the Manim Background Image Agent. "
        "Call the generate_manim_bg_images tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_manim_bg_images],
)
