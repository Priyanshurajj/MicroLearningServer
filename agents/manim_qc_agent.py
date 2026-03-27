import json
import os
import subprocess
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai
from .config import get_client, CODE_MODEL, ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")

MAX_FIX_ATTEMPTS = 3

MANIM_FIX_PROMPT = """The following Manim Community Edition Python code failed to render.

ERROR OUTPUT:
{error}

ORIGINAL CODE:
{code}

Fix the code so it renders successfully with `manim render -ql`.
Common issues to check:
- Deprecated API calls (use current Manim CE syntax)
- Missing imports (always use `from manim import *`)
- Incorrect MathTex/Tex syntax (escape backslashes properly)
- Invalid color names (use Manim color constants: WHITE, BLUE, RED, GREEN, YELLOW, etc.)
- Incorrect animation calls (Write for MathTex, Create for shapes, FadeIn/FadeOut)
- Scene class must inherit from Scene
- self.play() requires animation objects, not mobjects directly
- self.wait() for pauses
- Axes must use proper ranges

Return ONLY the corrected Python code. No explanations, no markdown code blocks.
"""


def execute_manim_qc(tool_context: ToolContext) -> dict:
    """Reads visual_output from session state and executes Manim QC."""
    visual_output_json = tool_context.state.get("visual_output", "")
    try:
        visual_data = json.loads(visual_output_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Manim QC: Cannot parse visual_output from state: {e}")
        return {"status": "error", "error": f"Cannot parse visual_output from state: {e}"}

    run_id = visual_data.get("run_id", "default")
    assets = visual_data.get("visual_assets", [])
    qc_results = []

    for asset in assets:
        if asset.get("asset_type") == "manim_code":
            result = _render_manim_with_retry(asset, run_id)
            qc_results.append(result)
        else:
            # Pass through image assets unchanged
            qc_results.append(asset)

    output = {
        "run_id": run_id,
        "qc_assets": qc_results,
        "manim_rendered": sum(
            1 for r in qc_results
            if r.get("asset_type") == "manim_video" and r.get("status") == "rendered"
        ),
        "manim_failed": sum(
            1 for r in qc_results
            if r.get("asset_type") in ("manim_video", "manim_code") and r.get("status") == "failed"
        ),
        "images_passed": sum(1 for r in qc_results if r.get("asset_type") == "image"),
        "total_assets": len(qc_results),
    }

    logger.info(
        f"Manim QC complete: {output['manim_rendered']} rendered, "
        f"{output['manim_failed']} failed, {output['images_passed']} images passed"
    )

    return {"status": "success", "qc_output": json.dumps(output)}


def _render_manim_with_retry(asset: dict, run_id: str) -> dict:
    """Attempt to render Manim code, auto-fix on failure up to MAX_FIX_ATTEMPTS times."""
    code_path = asset.get("code_file_path", "")
    scene_name = asset.get("scene_name", "")
    seg_id = asset.get("segment_id")
    manim_dir = os.path.join(OUTPUT_DIR, run_id, "manim")
    output_video = os.path.join(manim_dir, f"segment_{seg_id}.mp4")

    if not code_path or not os.path.exists(code_path):
        return {
            "segment_id": seg_id,
            "asset_type": "manim_video",
            "video_path": "",
            "status": "failed",
            "error": f"Code file not found: {code_path}",
            "render_attempts": 0,
        }

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        logger.info(f"Manim render attempt {attempt}/{MAX_FIX_ATTEMPTS} for segment {seg_id}")

        success, error_output = _run_manim_render(code_path, scene_name, manim_dir)

        if success:
            # Find the rendered video file
            rendered_path = _find_rendered_video(manim_dir, scene_name)
            if rendered_path:
                # Move to expected output path
                if rendered_path != output_video:
                    os.replace(rendered_path, output_video)

                logger.info(f"Manim segment {seg_id} rendered successfully on attempt {attempt}")
                return {
                    "segment_id": seg_id,
                    "asset_type": "manim_video",
                    "video_path": os.path.abspath(output_video),
                    "status": "rendered",
                    "render_attempts": attempt,
                }

        # If not last attempt, try to fix the code
        if attempt < MAX_FIX_ATTEMPTS:
            logger.warning(
                f"Manim render failed for segment {seg_id} (attempt {attempt}). "
                f"Attempting auto-fix..."
            )
            fixed = _auto_fix_code(code_path, error_output)
            if not fixed:
                logger.error(f"Auto-fix failed for segment {seg_id}")
                break

    return {
        "segment_id": seg_id,
        "asset_type": "manim_video",
        "video_path": "",
        "status": "failed",
        "error": f"Failed after {MAX_FIX_ATTEMPTS} attempts. Last error: {error_output[:500]}",
        "render_attempts": MAX_FIX_ATTEMPTS,
    }


def _run_manim_render(code_path: str, scene_name: str, output_dir: str) -> tuple[bool, str]:
    """Runs manim render as a subprocess. Returns (success, error_output)."""
    try:
        result = subprocess.run(
            [
                "python", "-m", "manim", "render",
                "-ql",  # Low quality for speed
                "--format", "mp4",
                "--media_dir", output_dir,
                code_path,
                scene_name,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(code_path),
        )

        if result.returncode == 0:
            return True, ""
        else:
            error = result.stderr or result.stdout
            return False, error

    except subprocess.TimeoutExpired:
        return False, "Manim render timed out after 120 seconds"
    except FileNotFoundError:
        return False, "Manim is not installed or not in PATH"
    except Exception as e:
        return False, str(e)


def _find_rendered_video(manim_dir: str, scene_name: str) -> str | None:
    """Searches for the rendered video file in Manim's output structure."""
    # Manim outputs to: media_dir/videos/{filename}/480p15/{scene_name}.mp4
    for root, dirs, files in os.walk(manim_dir):
        for f in files:
            if f.endswith(".mp4") and scene_name in f:
                return os.path.join(root, f)
    return None


def _auto_fix_code(code_path: str, error_output: str) -> bool:
    """Uses Gemini 2.5 Pro to fix broken Manim code."""
    try:
        with open(code_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        prompt = MANIM_FIX_PROMPT.format(
            error=error_output[:2000],
            code=original_code,
        )

        response = get_client().models.generate_content(
            model=CODE_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.1,  # Very low temperature for precise fixes
            ),
        )

        fixed_code = response.text.strip()

        # Strip markdown code fences if present
        if fixed_code.startswith("```python"):
            fixed_code = fixed_code[len("```python"):].strip()
        if fixed_code.startswith("```"):
            fixed_code = fixed_code[3:].strip()
        if fixed_code.endswith("```"):
            fixed_code = fixed_code[:-3].strip()

        # Overwrite the code file with fixed version
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(fixed_code)

        logger.info(f"Auto-fixed Manim code: {code_path}")
        return True

    except Exception as e:
        logger.error(f"Auto-fix failed: {e}")
        return False


manim_qc_agent = Agent(
    name="manim_qc_agent",
    model=ROUTING_MODEL,
    description=(
        "Executes Manim Python code in a subprocess, catches render errors, "
        "and uses Gemini 2.5 Pro to auto-heal broken code (up to 3 attempts). "
        "Passes through image assets unchanged."
    ),
    instruction=(
        "You are the Manim QC Agent. "
        "Call the execute_manim_qc tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[execute_manim_qc],
    output_key="qc_output",
)
