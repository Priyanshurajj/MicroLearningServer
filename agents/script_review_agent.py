import json
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai

from .config import get_client, TEXT_MODEL, ROUTING_MODEL

logger = logging.getLogger("EduReelADK")

SCRIPT_REVIEW_PROMPT = """You are a script quality reviewer for educational video production.

Review the following structured video script JSON and fix any issues found.

CHECKS TO PERFORM:
1. Every segment has a non-empty narration string
2. Every segment has a non-empty visual_description string
3. Every manim segment has math_expressions as a non-empty array (not null, not [])
4. No duplicate segment_id values
5. Segment IDs are integers; segments are orderable
6. math_expressions values are valid LaTeX strings (not plain text)
7. duration_seconds is a positive number (2.0 to 15.0 range)
8. Total segment count is between 3 and 9

If issues are found: fix them and return the corrected full JSON.
If everything looks good: return the JSON unchanged.

INPUT SCRIPT JSON:
{script_json}

OUTPUT: Return ONLY the corrected (or unchanged) full script JSON. No commentary.
"""


def review_script(tool_context: ToolContext) -> dict:
    """Validates and repairs script_output in session state."""
    script_json = tool_context.state.get("script_output", "")
    if not script_json:
        return {"status": "skipped", "reason": "No script_output in state"}

    try:
        # Quick structural validation before LLM review
        script = json.loads(script_json)
        segments = script.get("segments", [])
        if not segments:
            return {"status": "error", "error": "Script has no segments"}

        prompt = SCRIPT_REVIEW_PROMPT.format(script_json=script_json)

        response = get_client().models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        reviewed = json.loads(response.text)

        # Preserve run_id
        if "run_id" in script and "run_id" not in reviewed:
            reviewed["run_id"] = script["run_id"]

        reviewed_json = json.dumps(reviewed)
        tool_context.state["script_output"] = reviewed_json

        logger.info(
            f"Script review complete: {len(reviewed.get('segments', []))} segments"
        )
        return {"status": "success", "script_output": reviewed_json}

    except json.JSONDecodeError as e:
        logger.error(f"Script review returned invalid JSON: {e}")
        # Don't overwrite state if review failed — keep original
        return {"status": "error", "error": f"Review produced invalid JSON: {e}"}
    except Exception as e:
        logger.error(f"Script review failed: {e}")
        return {"status": "error", "error": str(e)}


script_review_agent = Agent(
    name="script_review_agent",
    model=ROUTING_MODEL,
    description=(
        "Validates the structured script JSON for completeness and correctness. "
        "Fixes issues like missing narrations, empty math_expressions arrays, "
        "and invalid LaTeX strings."
    ),
    instruction=(
        "You are the Script Review Agent. "
        "Call the review_script tool immediately — it reads data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[review_script],
)
