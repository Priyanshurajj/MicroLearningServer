import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai

from .config import get_client, CODE_MODEL, ROUTING_MODEL, OUTPUT_DIR

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
- If multiple math_expressions are provided, animate them IN SEQUENCE.
  Use Transform() or ReplacementTransform() to morph between consecutive equations
  to show derivation flow. Space them out to fill the target duration.

SEGMENT DETAILS:
- Narration: {narration}
- Visual Description: {visual_description}
- Math Expressions (animate in order): {math_expressions}
{manim_spec}

Return ONLY the Python code. No explanations, no markdown code blocks.
"""


def generate_manim_code(tool_context: ToolContext) -> dict:
    """Reads enhanced_script from state and generates Manim code for all manim segments."""
    script_json = tool_context.state.get("enhanced_script", "")
    if not script_json:
        script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Manim Code Agent: Cannot parse script from state: {e}")
        return {"status": "error", "error": f"Cannot parse script from state: {e}"}

    run_id = script.get("run_id", "default")
    manim_dir = os.path.join(OUTPUT_DIR, run_id, "manim")
    os.makedirs(manim_dir, exist_ok=True)

    manim_segments = [
        seg for seg in script.get("segments", [])
        if seg.get("segment_type") == "manim"
    ]

    if not manim_segments:
        result = {"run_id": run_id, "manim_assets": [], "total_manim": 0}
        tool_context.state["manim_code_output"] = json.dumps(result)
        return {"status": "success", "manim_code_output": json.dumps(result)}

    manim_assets = []

    with ThreadPoolExecutor(max_workers=min(len(manim_segments), 4)) as executor:
        futures = {
            executor.submit(_generate_single_manim_code, seg, manim_dir): seg
            for seg in manim_segments
        }
        for future in as_completed(futures):
            manim_assets.append(future.result())

    manim_assets.sort(key=lambda x: x["segment_id"])

    result = {
        "run_id": run_id,
        "manim_assets": manim_assets,
        "total_manim": len(manim_assets),
        "generated": sum(1 for a in manim_assets if a["status"] == "code_generated"),
        "failed": sum(1 for a in manim_assets if a["status"] == "failed"),
    }

    logger.info(
        f"Manim Code Agent: {result['generated']} scripts generated, "
        f"{result['failed']} failed"
    )

    manim_code_output_json = json.dumps(result)
    tool_context.state["manim_code_output"] = manim_code_output_json
    return {"status": "success", "manim_code_output": manim_code_output_json}


def _generate_single_manim_code(seg: dict, manim_dir: str) -> dict:
    """Generates Manim Python code for one manim segment."""
    seg_id = seg["segment_id"]
    code_path = os.path.join(manim_dir, f"segment_{seg_id}.py")

    # Support both math_expressions[] and legacy math_expression
    math_exprs = seg.get("math_expressions") or (
        [seg["math_expression"]] if seg.get("math_expression") else []
    )
    math_exprs = [e for e in math_exprs if e]  # filter None/empty

    manim_spec_str = ""
    if "manim_spec" in seg:
        manim_spec_str = (
            f"- Manim Specification: {json.dumps(seg['manim_spec'], indent=2)}"
        )

    prompt = MANIM_CODE_PROMPT.format(
        segment_id=seg_id,
        duration=seg.get("duration_seconds", 8),
        narration=seg.get("narration", ""),
        visual_description=seg.get("visual_description", ""),
        math_expressions=json.dumps(math_exprs) if math_exprs else "[]",
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

        # Strip markdown code fences
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
            "scene_name": f"Segment{seg_id}Scene",
            "status": "failed",
            "error": str(e),
        }


manim_code_agent = Agent(
    name="manim_code_agent",
    model=ROUTING_MODEL,
    description=(
        "Generates Manim Python animation code for all manim segments using Gemini 2.5 Pro. "
        "Supports multiple equations per segment via math_expressions[]."
    ),
    instruction=(
        "You are the Manim Code Agent. "
        "Call the generate_manim_code tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_manim_code],
)
