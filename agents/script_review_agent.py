from google.adk.agents import Agent
from google import genai

from .config import TEXT_MODEL

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
{script_output}

OUTPUT: Return ONLY the corrected (or unchanged) full script JSON. No commentary.
"""

script_review_agent = Agent(
    name="script_review_agent",
    model=TEXT_MODEL,
    description=(
        "Validates the structured script JSON for completeness and correctness. "
        "Fixes issues like missing narrations, empty math_expressions arrays, "
        "and invalid LaTeX strings."
    ),
    instruction=SCRIPT_REVIEW_PROMPT,
    output_key="script_output",
    generate_content_config=genai.types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
    ),
)
