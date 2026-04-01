import json
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai

from .config import get_client, TEXT_MODEL, ROUTING_MODEL

logger = logging.getLogger("EduReelADK")

PROMPT_REVIEW_PROMPT = """You are a content safety and quality reviewer for AI-generated educational video prompts.

Review the following enhanced script JSON and fix any issues found.

CHECKS FOR general SEGMENTS:
1. image_prompt exists and is non-empty
2. image_prompt does not contain potentially policy-violating content
   (violence, explicit content, real named individuals, copyrighted characters)
   → Rewrite such prompts with safe educational alternatives
3. image_prompt clearly specifies photorealistic/cinematic style
   (if it mentions cartoon/flat/illustration, rewrite to photorealistic)

CHECKS FOR manim SEGMENTS:
1. manim_spec exists and has: scene_description, animations (non-empty array),
   color_scheme (non-empty array), math_elements (non-empty array)
2. background_image field exists (true or false)
3. If background_image is true, image_prompt must also exist and be descriptive

CHECKS FOR text_overlay (when present):
1. lines is a non-empty array of strings
2. highlight_words is a non-empty array of strings
3. highlight_words are substrings of at least one line

If issues found: fix them and return the corrected full JSON.
If clean: return unchanged.

INPUT ENHANCED SCRIPT JSON:
{enhanced_script_json}

OUTPUT: Return ONLY the corrected (or unchanged) full enhanced script JSON. No commentary.
"""


def review_prompts(tool_context: ToolContext) -> dict:
    """Validates and repairs enhanced_script in session state."""
    enhanced_json = tool_context.state.get("enhanced_script", "")
    if not enhanced_json:
        return {"status": "skipped", "reason": "No enhanced_script in state"}

    try:
        enhanced = json.loads(enhanced_json)
        segments = enhanced.get("segments", [])
        if not segments:
            return {"status": "error", "error": "Enhanced script has no segments"}

        prompt = PROMPT_REVIEW_PROMPT.format(enhanced_script_json=enhanced_json)

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
        if "run_id" in enhanced and "run_id" not in reviewed:
            reviewed["run_id"] = enhanced["run_id"]

        reviewed_json = json.dumps(reviewed)
        tool_context.state["enhanced_script"] = reviewed_json

        logger.info(
            f"Prompt review complete: {len(reviewed.get('segments', []))} segments reviewed"
        )
        return {"status": "success", "enhanced_script": reviewed_json}

    except json.JSONDecodeError as e:
        logger.error(f"Prompt review returned invalid JSON: {e}")
        return {"status": "error", "error": f"Review produced invalid JSON: {e}"}
    except Exception as e:
        logger.error(f"Prompt review failed: {e}")
        return {"status": "error", "error": str(e)}


prompt_review_agent = Agent(
    name="prompt_review_agent",
    model=ROUTING_MODEL,
    description=(
        "Reviews enhanced_script for content safety and structural completeness. "
        "Rewrites policy-violating image prompts and fills in missing manim_spec fields."
    ),
    instruction=(
        "You are the Prompt Review Agent. "
        "Call the review_prompts tool immediately — it reads data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[review_prompts],
)
