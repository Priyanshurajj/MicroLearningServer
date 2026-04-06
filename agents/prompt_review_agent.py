from google.adk.agents import Agent
from google import genai

from .config import TEXT_MODEL

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
{enhanced_script}

OUTPUT: Return ONLY the corrected (or unchanged) full enhanced script JSON. No commentary.
"""

prompt_review_agent = Agent(
    name="prompt_review_agent",
    model=TEXT_MODEL,
    description=(
        "Reviews enhanced_script for content safety and structural completeness. "
        "Rewrites policy-violating image prompts and fills in missing manim_spec fields."
    ),
    instruction=PROMPT_REVIEW_PROMPT,
    output_key="enhanced_script",
    generate_content_config=genai.types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
    ),
)
