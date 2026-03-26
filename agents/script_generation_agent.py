import json
import uuid
import os
import logging

from google.adk.agents import Agent
from google import genai
from .config import get_client, TEXT_MODEL, ROUTING_MODEL, OUTPUT_DIR

logger = logging.getLogger("EduReelADK")

SCRIPT_GENERATION_PROMPT = """You are an expert educational content scriptwriter specializing in short-form video reels (30-90 seconds).

Given the following topic or transcript, create a structured video script.

RULES:
1. Break the content into 3-6 short segments (5-10 seconds each).
2. For EACH segment, determine its type:
   - "general": Normal educational content (explanations, introductions, real-world examples, summaries)
   - "maths": Mathematical or scientific content that requires equations, formulas, graphs, geometric shapes, or animated derivations
3. A single video CAN have BOTH general and maths segments mixed together.
4. Each segment must have a clear narration text and a detailed visual description.
5. For maths segments, include the exact math_expression (in LaTeX format) to be animated.
6. Narration should be conversational, engaging, and suitable for a young audience.
7. Visual descriptions should be specific enough for an AI image/animation generator.

TOPIC/TRANSCRIPT:
{transcript}

OUTPUT FORMAT (strict JSON):
{{
    "title": "Short catchy title for the reel",
    "topic": "Brief topic summary",
    "segments": [
        {{
            "segment_id": 1,
            "segment_type": "general",
            "narration": "Engaging narration text for this segment...",
            "visual_description": "Detailed description of what should appear visually...",
            "duration_seconds": 5.0,
            "math_expression": null
        }},
        {{
            "segment_id": 2,
            "segment_type": "maths",
            "narration": "Now let's look at the formula...",
            "visual_description": "Animated equation showing step-by-step derivation...",
            "duration_seconds": 8.0,
            "math_expression": "a^2 + b^2 = c^2"
        }}
    ],
    "total_duration_seconds": 25.0
}}
"""


def generate_script(transcript: str) -> dict:
    """Generates a structured educational video script from a transcript using Gemini."""
    try:
        prompt = SCRIPT_GENERATION_PROMPT.format(transcript=transcript)

        response = get_client().models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )

        script_text = response.text
        script_data = json.loads(script_text)

        # Inject a unique run_id for output directory management
        run_id = uuid.uuid4().hex[:8]
        script_data["run_id"] = run_id

        # Create output directories for this run
        run_dir = os.path.join(OUTPUT_DIR, run_id)
        for subdir in ["audio", "images", "manim"]:
            os.makedirs(os.path.join(run_dir, subdir), exist_ok=True)

        logger.info(
            f"Script generated: {len(script_data.get('segments', []))} segments, "
            f"run_id={run_id}"
        )

        return {"status": "success", "script": json.dumps(script_data)}

    except json.JSONDecodeError as e:
        logger.error(f"Script generation returned invalid JSON: {e}")
        return {"status": "error", "error": f"Invalid JSON from Gemini: {str(e)}"}
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        return {"status": "error", "error": str(e)}


script_agent = Agent(
    name="script_agent",
    model=ROUTING_MODEL,
    description="Generates a structured educational script with per-segment type classification.",
    instruction=(
        "You are the Script Generation Agent. "
        "When you receive a transcript or topic from the user, call the generate_script "
        "tool with the full transcript text. "
        "Return ONLY the raw JSON string from the tool's 'script' field as your output. "
        "Do not add any commentary, formatting, or markdown."
    ),
    tools=[generate_script],
    output_key="script_output",
)
