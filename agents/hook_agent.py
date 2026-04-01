import json
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google import genai

from .config import get_client, TEXT_MODEL, ROUTING_MODEL

logger = logging.getLogger("EduReelADK")

HOOK_GENERATION_PROMPT = """You are an expert short-form video hook writer for educational reels.

Given the following educational content transcript, generate ONE dramatic opening hook segment
that will appear at the very start of the video (before any explanations).

THE HOOK MUST:
- Pose a surprising, counterintuitive, or mind-bending question related to the topic
- Create immediate curiosity ("Did you know...", "What if...", "Why does...")
- Be completable in 6 seconds of narration (max 2 short sentences)
- Leave the viewer WANTING to know the answer (which the rest of the video provides)
- Have a dramatic, high-impact visual description suitable for a cinematic Imagen image

TRANSCRIPT:
{transcript}

OUTPUT (strict JSON, ONE segment object):
{{
    "segment_id": 0,
    "segment_type": "general",
    "is_hook": true,
    "narration": "Short dramatic hook narration (max 2 sentences)...",
    "visual_description": "Dramatic cinematic scene description...",
    "image_prompt": "Photorealistic cinematic image: [detailed Imagen prompt, 8K, dramatic lighting, BBC documentary style]",
    "duration_seconds": 6.0,
    "math_expression": null,
    "math_expressions": []
}}
"""


def generate_hook_segment(tool_context: ToolContext) -> dict:
    """Generates a curiosity hook opening segment and stores it in session state."""
    transcript = tool_context.state.get("narrative_transcript", "").strip()
    if not transcript:
        logger.warning("Hook Agent: No narrative_transcript in state — skipping hook")
        return {"status": "skipped", "reason": "No transcript available"}

    try:
        prompt = HOOK_GENERATION_PROMPT.format(transcript=transcript[:3000])

        response = get_client().models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.9,
            ),
        )

        hook_segment = json.loads(response.text)

        # Enforce required fields
        hook_segment["segment_id"] = 0
        hook_segment["segment_type"] = "general"
        hook_segment["is_hook"] = True
        hook_segment.setdefault("duration_seconds", 6.0)
        hook_segment.setdefault("math_expression", None)
        hook_segment.setdefault("math_expressions", [])

        hook_json = json.dumps(hook_segment)
        tool_context.state["hook_segment"] = hook_json

        logger.info(
            f"Hook segment generated: \"{hook_segment.get('narration', '')[:80]}\""
        )
        return {"status": "success", "hook_segment": hook_json}

    except json.JSONDecodeError as e:
        logger.error(f"Hook Agent returned invalid JSON: {e}")
        return {"status": "error", "error": f"Invalid JSON: {e}"}
    except Exception as e:
        logger.error(f"Hook generation failed: {e}")
        return {"status": "error", "error": str(e)}


hook_agent = Agent(
    name="hook_agent",
    model=ROUTING_MODEL,
    description=(
        "Generates a 6-second curiosity hook opening segment that poses a "
        "surprising question before the main educational content begins."
    ),
    instruction=(
        "You are the Hook Agent. "
        "Call the generate_hook_segment tool immediately — it reads data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_hook_segment],
)
