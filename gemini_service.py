"""
gemini_service.py - Gemini API integration using google-genai SDK.

Provides:
    - generate_script(text) → structured slide script with image prompts
    - generate_image(prompt, save_path) → AI-generated image via Imagen
    - generate_teacher_image(save_path) → consistent teacher character
"""

import os
import json
import re
from pathlib import Path

import urllib.parse
import requests

from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("[GEMINI] API key loaded and client initialized.")
else:
    client = None
    print("[GEMINI] WARNING: GEMINI_API_KEY not found. AI features will fail.")

# Models
TEXT_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Script Generation
# ---------------------------------------------------------------------------

def generate_script(text: str) -> dict | None:
    """Generate a micro-learning script from input text.

    Returns a dict with keys: summary, content_type, slides.
    Each slide has: title, content, image_prompt, scene_mood.
    """
    if not client:
        print("[GEMINI] ERROR: No client configured.")
        return None

    prompt = f"""You are an educational content creator specializing in micro-learning.

Given the following text, create a 60-second micro-learning script split into slides.

Return your response as pure JSON (no markdown, no code fences, no extra text) in this exact format:
{{
    "summary": "A 2-3 line summary of the key content",
    "content_type": "general" or "math",
    "slides": [
        {{
            "title": "Slide Title",
            "content": "2-3 lines of educational content",
            "image_prompt": "A detailed visual description for AI image generation. Describe the scene, objects, colors, style, and mood. Use descriptive terms like 'educational illustration', 'warm lighting', 'vibrant colors'. This will be used to generate a background image for this slide.",
            "scene_mood": "one of: bright, dark, warm, cool, energetic, calm, dramatic, playful"
        }}
    ]
}}

Rules:
- The summary should capture the essence of the content in 2-3 lines.
- Set content_type to "math" ONLY if the content is primarily about mathematics, equations, formulas, or calculations. Otherwise set it to "general".
- Each slide should have a clear, concise title.
- Each slide's content should be 2-3 lines, easy to read and understand.
- Each slide's image_prompt should describe a vivid, relevant background scene (NO text or words in the image). Use descriptive art direction. Example: "A lush green forest canopy with sunlight filtering through leaves, educational nature photography style, warm golden light, slightly blurred background"
- scene_mood should match the emotional tone of the slide content.
- Aim for 5-7 slides total.
- Make the content engaging and educational.
- Return ONLY the JSON object, nothing else.

Text to process:
---
{text}
---"""

    try:
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=[prompt],
        )

        response_text = response.text.strip()

        # Strip markdown code fences if present
        response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
        response_text = re.sub(r"\s*```$", "", response_text)
        response_text = response_text.strip()

        script = json.loads(response_text)

        if "summary" not in script or "slides" not in script:
            print("[GEMINI] ERROR: Response missing required keys ('summary', 'slides').")
            return None

        if not isinstance(script["slides"], list) or len(script["slides"]) == 0:
            print("[GEMINI] ERROR: 'slides' must be a non-empty list.")
            return None

        # Ensure content_type is present and valid
        if script.get("content_type") not in ("math", "general"):
            script["content_type"] = "general"

        # Ensure every slide has image_prompt and scene_mood
        for slide in script["slides"]:
            if "image_prompt" not in slide:
                slide["image_prompt"] = f"Educational illustration about {slide.get('title', 'learning')}, clean modern style, vibrant colors"
            if "scene_mood" not in slide:
                slide["scene_mood"] = "bright"

        print(f"[GEMINI] Script generated: {len(script['slides'])} slides, type={script['content_type']}")
        return script

    except json.JSONDecodeError as e:
        print(f"[GEMINI] ERROR: Failed to parse response as JSON: {e}")
        return None
    except Exception as e:
        print(f"[GEMINI] ERROR: Unexpected error during script generation: {e}")
        return None


# ---------------------------------------------------------------------------
# Image Generation
# ---------------------------------------------------------------------------

def generate_image(prompt: str, save_path: str) -> str | None:
    """Generate an image from a text prompt using Pollinations.ai (Free API).

    Args:
        prompt: Descriptive text for the image to generate.
        save_path: File path to save the generated image.

    Returns:
        The save_path if successful, None otherwise.
    """
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        # Using Pollinations API (100% free, no key required)
        # Adding seed to get somewhat consistent art style
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true"
        
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Ensure parent directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"[POLLINATIONS] Image saved: {save_path}")
        return save_path

    except Exception as e:
        print(f"[POLLINATIONS] ERROR generating image: {e}")
        return None


def generate_teacher_image(save_path: str) -> str | None:
    """Generate a teacher character illustration.

    Creates a half-body portrait of a friendly teacher character
    suitable for overlaying on video slides.

    Args:
        save_path: File path to save the teacher image.

    Returns:
        The save_path if successful, None otherwise.
    """
    teacher_prompt = (
        "A friendly professional female teacher in a dark blue blazer and white shirt, "
        "half-body portrait, standing pose facing slightly to the right, warm smile, "
        "hand gesture as if explaining something, clean solid dark blue background (#1a1a2e), "
        "modern flat illustration style with soft shading, suitable for educational video overlay, "
        "high quality, no text, no watermark"
    )

    return generate_image(teacher_prompt, save_path)
