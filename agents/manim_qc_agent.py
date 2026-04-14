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
- Transform/ReplacementTransform requires two mobjects of the same type

Return ONLY the corrected Python code. No explanations, no markdown code blocks.
"""


def execute_manim_qc(tool_context: ToolContext) -> dict:
    manim_code_json = tool_context.state.get("manim_code_output", "")
    bg_image_json = tool_context.state.get("bg_image_output", "{}")
    enhanced_script_json = tool_context.state.get("enhanced_script", "{}")
    if not enhanced_script_json:
        enhanced_script_json = tool_context.state.get("script_output", "{}")

    try:
        manim_data = json.loads(manim_code_json) if manim_code_json else {"manim_assets": []}
        bg_data = json.loads(bg_image_json) if bg_image_json else {"bg_images": []}
        script_data = json.loads(enhanced_script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Manim QC: Cannot parse state: {e}")
        return {"status": "error", "error": f"Cannot parse state: {e}"}

    run_id = manim_data.get("run_id") or bg_data.get("run_id", "default")

    # Build background image lookup: segment_id → file path (from manim_bg_image_agent output)
    bg_lookup: dict[int, str] = {
        img["segment_id"]: img["image_file_path"]
        for img in bg_data.get("bg_images", [])
        if img.get("image_file_path") and img.get("status") == "generated"
    }

    manim_assets = manim_data.get("manim_assets", [])
    qc_results = []

    for asset in manim_assets:
        result = _render_manim_with_retry(asset, run_id, script_data)
        # Attach background image path if available for this segment
        seg_id = result.get("segment_id")
        if seg_id in bg_lookup:
            result["background_image_path"] = bg_lookup[seg_id]
        qc_results.append(result)

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
        "total_manim": len(qc_results),
    }

    logger.info(
        f"Manim QC complete: {output['manim_rendered']} rendered, "
        f"{output['manim_failed']} failed"
    )

    qc_output_json = json.dumps(output)
    tool_context.state["qc_output"] = qc_output_json
    return {"status": "success", "qc_output": qc_output_json}


def _render_manim_with_retry(asset: dict, run_id: str, script_data: dict) -> dict:
    code_path = asset.get("code_file_path", "")
    scene_name = asset.get("scene_name", "")
    seg_id = asset.get("segment_id")
    manim_dir = os.path.join(OUTPUT_DIR, run_id, "manim")
    output_video = os.path.join(manim_dir, f"segment_{seg_id}.mov")

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
            rendered_path = _find_rendered_video(manim_dir, scene_name)
            if rendered_path:
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

        if attempt < MAX_FIX_ATTEMPTS:
            logger.warning(
                f"Manim render failed for segment {seg_id} (attempt {attempt}). "
                f"Attempting auto-fix..."
            )
            fixed = _auto_fix_code(code_path, error_output)
            if not fixed:
                logger.error(f"Auto-fix failed for segment {seg_id}")
                break

    # All attempts failed — try fallback static text animation
    logger.warning(
        f"Manim render failed all {MAX_FIX_ATTEMPTS} attempts for segment {seg_id}. "
        f"Generating fallback generic Manim script..."
    )

    fallback_code = _generate_fallback_manim_code(asset, script_data)
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(fallback_code)

    logger.info(f"Rendering fallback script for segment {seg_id}...")
    success, error_output = _run_manim_render(code_path, scene_name, manim_dir)

    if success:
        rendered_path = _find_rendered_video(manim_dir, scene_name)
        if rendered_path:
            if rendered_path != output_video:
                os.replace(rendered_path, output_video)
            logger.info(f"Fallback Manim segment {seg_id} rendered successfully")
            return {
                "segment_id": seg_id,
                "asset_type": "manim_video",
                "video_path": os.path.abspath(output_video),
                "status": "rendered",
                "render_attempts": MAX_FIX_ATTEMPTS + 1,
                "is_fallback": True,
            }

    return {
        "segment_id": seg_id,
        "asset_type": "manim_video",
        "video_path": "",
        "status": "failed",
        "error": f"Failed after {MAX_FIX_ATTEMPTS} attempts and fallback. Last error: {error_output[:500]}",
        "render_attempts": MAX_FIX_ATTEMPTS + 1,
    }


def _generate_fallback_manim_code(asset: dict, script_data: dict) -> str:
    """Generates a reliable fallback Scene using a simple text card layout."""
    seg_id = asset.get("segment_id")
    scene_name = asset.get("scene_name", f"Segment{seg_id}Scene")

    segments = script_data.get("segments", [])
    target_seg = next((s for s in segments if s.get("segment_id") == seg_id), {})
    narration = target_seg.get("narration", "Educational Content")
    title = script_data.get("title", f"Segment {seg_id}")

    narration = narration.replace('"', '\\"').replace('\n', ' ')
    title = title.replace('"', '\\"').replace('\n', ' ')

    return f'''from manim import *
import textwrap

class {scene_name}(Scene):
    def construct(self):
        # Subtle background grid for depth
        grid = NumberPlane(
            background_line_style={{"stroke_color": BLUE_E, "stroke_opacity": 0.1}},
            axis_config={{"stroke_opacity": 0}},
            faded_line_ratio=2,
        )
        self.add(grid)

        title_text = "{title}"
        content_text = "{narration}"

        wrapped_title = textwrap.fill(title_text, width=28)
        title_obj = Text(wrapped_title, font_size=48, color=WHITE, weight="BOLD")
        title_obj.to_edge(UP, buff=1.5)

        underline = Line(
            title_obj.get_left() + DOWN * 0.3,
            title_obj.get_right() + DOWN * 0.3,
            color=YELLOW,
            stroke_width=3,
        )

        wrapped_content = textwrap.fill(content_text, width=38)
        content_obj = Text(
            wrapped_content, font_size=30, color=GREY_A, line_spacing=0.9
        )
        content_obj.next_to(underline, DOWN, buff=0.8)

        self.play(Write(title_obj), run_time=1.2)
        self.play(FadeIn(underline, shift=RIGHT * 0.5), run_time=0.6)
        self.wait(0.3)
        self.play(FadeIn(content_obj, shift=UP * 0.3), run_time=1.0)
        self.wait(1.5)
        self.play(
            *[FadeOut(mob) for mob in self.mobjects if mob is not grid],
            run_time=0.6,
        )
        self.wait(0.3)
'''


def _run_manim_render(code_path: str, scene_name: str, output_dir: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [
                "python", "-m", "manim", "render",
                "-ql",
                "--progress_bar", "display",
                "-t",
                "--format", "mov",
                "--media_dir", output_dir,
                code_path,
                scene_name,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(code_path),
        )

        log_file = os.path.join(output_dir, f"manim_{scene_name}_exec.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"--- Manim Render Output for {scene_name} ---\n")
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\nSTDERR:\n")
            f.write(result.stderr)
            f.write("-" * 50 + "\n")

        if result.returncode == 0:
            return True, ""
        else:
            error = result.stderr or result.stdout
            logger.error(
                f"Manim rendering failed (exit code {result.returncode}). "
                f"Check {log_file} for details."
            )
            logger.error(f"Error preview: {error[:500]}")
            return False, error

    except subprocess.TimeoutExpired:
        return False, "Manim render timed out after 120 seconds"
    except FileNotFoundError:
        return False, "Manim is not installed or not in PATH"
    except Exception as e:
        return False, str(e)


def _find_rendered_video(manim_dir: str, scene_name: str) -> str | None:
    for root, _, files in os.walk(manim_dir):
        for f in files:
            if (f.endswith(".mp4") or f.endswith(".mov") or f.endswith(".webm")) and scene_name in f:
                return os.path.join(root, f)
    return None


def _auto_fix_code(code_path: str, error_output: str) -> bool:
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
                temperature=0.1,
            ),
        )

        fixed_code = response.text.strip()

        if fixed_code.startswith("```python"):
            fixed_code = fixed_code[len("```python"):].strip()
        if fixed_code.startswith("```"):
            fixed_code = fixed_code[3:].strip()
        if fixed_code.endswith("```"):
            fixed_code = fixed_code[:-3].strip()

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
        "Attaches background image paths to rendered Manim assets."
    ),
    instruction=(
        "You are the Manim QC Agent. "
        "Call the execute_manim_qc tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[execute_manim_qc],
)
