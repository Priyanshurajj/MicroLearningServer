import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai

from .config import get_client, CODE_MODEL, ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")

MANIM_CODE_PROMPT = """You are an elite Manim Community Edition animator producing cinematic, 3Blue1Brown-quality educational animations.
Generate a complete, self-contained Manim script for the following segment.

─── MANDATORY REQUIREMENTS ───────────────────────────────────────────────────
- `from manim import *` — only import
- Exactly ONE Scene class named `Segment{segment_id}Scene`
- Must render with `manim render -ql` — zero errors
- No external files, no images, no SVGs
- Target duration: ~{duration} seconds

─── VISUAL STYLE ─────────────────────────────────────────────────────────────
Background & Depth:
- Keep default BLACK background
- Add a subtle grid or faint coordinate plane for math scenes when appropriate:
    grid = NumberPlane(background_line_style={{"stroke_color": BLUE_E, "stroke_opacity": 0.15}})
- Use a thin decorative underline (Line or Underline) beneath titles for polish

Typography & Color Palette:
- Title (Tex): font_size=52, color=WHITE, weight=BOLD
- Main equations (MathTex): font_size=64, color=WHITE
- Intermediate steps or labels (Tex): font_size=42, color=GREY_A
- Key result / answer: color=YELLOW  — highlight with SurroundingRectangle(color=YELLOW, buff=0.2, corner_radius=0.1)
- Accent geometry: BLUE_C, TEAL_C
- Error / warning: RED_C
- Strict 4-color maximum per scene: WHITE, YELLOW, BLUE_C, TEAL_C

Layout & Spacing:
- Minimum 0.8 MU between elements — use .next_to(buff=0.5), .to_edge(), .shift()
- Never hardcode pixel coordinates
- VGroup() related elements and use .arrange(DOWN, buff=0.6) for vertical stacks
- Center primary content; secondary content to edges

─── ANIMATION CHOREOGRAPHY ───────────────────────────────────────────────────
Pacing — smooth, deliberate, cinematic:

1. OPENING (0-2s):
   - Write(title, run_time=1.2) then self.wait(0.4)
   - FadeIn(underline, shift=RIGHT*0.5, run_time=0.6)

2. BUILDING CONTENT (middle):
   - Equations: FadeIn(eq, shift=UP*0.3, run_time=0.8)
   - Derivation flow: TransformMatchingTex(old_eq, new_eq, run_time=1.5) — preferred over ReplacementTransform for MathTex
   - If TransformMatchingTex is not suitable, use ReplacementTransform(old, new, run_time=1.5)
   - Labels / annotations: Write(label, run_time=0.8), or FadeIn(label, shift=DOWN*0.2)
   - Arrows or pointers: GrowArrow(arrow, run_time=0.6)
   - Geometry: Create(shape, run_time=1.0) or DrawBorderThenFill(shape, run_time=1.2)
   - Add self.wait(0.3) between major steps for breathing room

3. EMPHASIS / REVEAL:
   - Key result: Circumscribe(target, color=YELLOW, run_time=1.0, fade_out=True)
   - Alternative: Indicate(target, color=YELLOW, scale_factor=1.1, run_time=0.8)
   - Box a final answer: SurroundingRectangle(answer, color=YELLOW, buff=0.2, corner_radius=0.1)

4. TRANSITIONS between sections:
   - FadeOut(*old_group, shift=DOWN*0.3, run_time=0.5) before new content
   - Or: old_group.animate.shift(UP*3).set_opacity(0) with run_time=0.8

5. CLOSING (last 1-2s):
   - self.play(*[FadeOut(mob) for mob in self.mobjects if mob is not None], run_time=0.6)
   - self.wait(0.5)

─── ADVANCED TECHNIQUES (use where appropriate) ──────────────────────────────
- Progressive reveal: Show equation parts one-by-one using .set_opacity(0) then .animate.set_opacity(1)
- Number line / Axes for graphing: use Axes() with proper ranges and labels
- Brace + label: Brace(target, direction=DOWN) with label.next_to(brace, DOWN)
- Tracker animations: ValueTracker for smooth parameter changes
- Color transforms: target.animate.set_color(YELLOW) to highlight dynamically

─── PROHIBITED ───────────────────────────────────────────────────────────────
- Flash() — causes render failures in some environments
- ShowCreation() — deprecated, use Create() instead
- Hardcoded pixel coordinates — always use relative positioning
- Font sizes below 32
- More than 4 colors in one scene
- Overlapping elements — always check spacing
- self.camera.frame operations (not supported in -ql mode without MovingCameraScene)
- Using MovingCameraScene (stick to Scene for reliability)

─── MULTIPLE EQUATIONS ───────────────────────────────────────────────────────
If math_expressions has more than one item, show them IN SEQUENCE.
Prefer TransformMatchingTex() for MathTex morphing to show derivation flow.
Fade out previous equation groups before introducing unrelated new content.
Space animations evenly to fill the full target duration.
Add self.wait(0.3-0.5) between each major animation step.

─── SEGMENT DETAILS ──────────────────────────────────────────────────────────
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
