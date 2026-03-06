import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("[GEMINI] API key loaded and configured.")
else:
    print("[GEMINI] WARNING: GEMINI_API_KEY not found in environment. AI features will fail.")

MODEL_NAME = "gemini-3-flash-preview"

def generate_script(text: str) -> dict | None:
    if not GEMINI_API_KEY:
        print("[GEMINI] ERROR: No API key configured. Cannot generate script.")
        return None

    prompt = f"""You are an educational content creator specializing in micro-learning.

Given the following text, create a 60-second micro-learning script split into 10-12 slides.

Return your response as pure JSON (no markdown, no code fences, no extra text) in this exact format:
{{
    "summary": "A 2-3 line summary of the key content",
    "slides": [
        {{"title": "Slide Title", "content": "2-3 lines of educational content"}},
        {{"title": "Slide Title", "content": "2-3 lines of educational content"}}
    ]
}}

Rules:
- The summary should capture the essence of the content in 2-3 lines.
- Each slide should have a clear, concise title.
- Each slide's content should be 2-3 lines, easy to read and understand.
- Aim for 5-7 slides total.
- Make the content engaging and educational.
- Return ONLY the JSON object, nothing else.

Text to process:
---
{text}
---"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)

        response_text = response.text.strip()
        
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

        print(f"[GEMINI] Script generated successfully with {len(script['slides'])} slides.")
        return script

    except json.JSONDecodeError as e:
        print(f"[GEMINI] ERROR: Failed to parse response as JSON: {e}")
        return None
    except Exception as e:
        print(f"[GEMINI] ERROR: Unexpected error during script generation: {e}")
        return None
