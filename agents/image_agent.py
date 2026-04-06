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


def generate_images(tool_context: ToolContext) -> dict:
    """Reads enhanced_script from state and generates Imagen images for general segments only."""
    script_json = tool_context.state.get("enhanced_script", "")
    if not script_json:
        script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Image Agent: Cannot parse script from state: {e}")
        return {"status": "error", "error": f"Cannot parse script from state: {e}"}

    run_id = script.get("run_id", "default")
    images_dir = os.path.join(OUTPUT_DIR, run_id, "images")
    os.makedirs(images_dir, exist_ok=True)

    general_segments = [
        seg for seg in script.get("segments", [])
        if seg.get("segment_type", "general") == "general"
    ]

    if not general_segments:
        result = {"run_id": run_id, "images": [], "total_images": 0}
        tool_context.state["image_output"] = json.dumps(result)
        return {"status": "success", "image_output": json.dumps(result)}

    images = []

    with ThreadPoolExecutor(max_workers=min(len(general_segments), 5)) as executor:
        futures = {
            executor.submit(_generate_single_image, seg, images_dir): seg
            for seg in general_segments
        }
        for future in as_completed(futures):
            images.append(future.result())

    images.sort(key=lambda x: x["segment_id"])

    result = {
        "run_id": run_id,
        "images": images,
        "total_images": len(images),
    }

    logger.info(f"Image Agent: {len(images)} general images generated")

    image_output_json = json.dumps(result)
    tool_context.state["image_output"] = image_output_json
    return {"status": "success", "image_output": image_output_json}


def _generate_single_image(seg: dict, images_dir: str) -> dict:
    """Generates one cinematic image for a general segment."""
    seg_id = seg["segment_id"]
    output_path = os.path.join(images_dir, f"segment_{seg_id}.png")

    prompt = seg.get(
        "image_prompt",
        seg.get("enhanced_visual", seg.get("visual_description", "Educational illustration")),
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


image_agent = Agent(
    name="image_agent",
    model=ROUTING_MODEL,
    description=(
        "Generates photorealistic cinematic Imagen images for general segments only. "
        "Part of general_pipeline. Manim backgrounds handled by manim_bg_image_agent."
    ),
    instruction=(
        "You are the Image Agent. "
        "Call the generate_images tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_images],
)
