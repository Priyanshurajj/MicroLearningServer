import json
from google.adk.agents import Agent


def generate_script(transcript: str) -> dict:
    math_keywords = [
        "theorem", "equation", "formula", "calculate", "algebra",
        "geometry", "calculus", "derivative", "integral", "pythagorean",
        "quadratic", "polynomial", "trigonometry", "matrix", "vector",
        "proof", "axiom", "logarithm", "probability", "statistics",
        "a^2", "b^2", "c^2", "x^2", "f(x)", "sin", "cos", "tan",
    ]
    transcript_lower = transcript.lower()
    is_math = any(kw in transcript_lower for kw in math_keywords)
    content_type = "maths" if is_math else "general"

    dummy_script = {
        "title": f"Learn About: {transcript[:50]}...",
        "topic": transcript[:100],
        "content_type": content_type,
        "segments": [
            {
                "segment_id": 1,
                "narration": f"Welcome! Today we'll explore an interesting topic. {transcript[:80]}",
                "visual_description": "An engaging title card with the topic name displayed prominently with animated background",
                "duration_seconds": 5.0,
            },
            {
                "segment_id": 2,
                "narration": f"Let's dive deeper into the key concepts. {transcript[80:200] if len(transcript) > 80 else 'This is a fascinating subject with many applications.'}",
                "visual_description": "Illustrative diagram showing the main concept with labeled parts and arrows",
                "duration_seconds": 8.0,
            },
            {
                "segment_id": 3,
                "narration": "Here's a practical example to help you understand better. Notice how everything connects together.",
                "visual_description": "Real-world example visualization with step-by-step annotations",
                "duration_seconds": 7.0,
            },
            {
                "segment_id": 4,
                "narration": "To summarize what we've learned today - remember these key takeaways for your studies!",
                "visual_description": "Summary card with bullet points of key takeaways and a call-to-action",
                "duration_seconds": 5.0,
            },
        ],
        "total_duration_seconds": 25.0,
    }

    return {"status": "success", "script": json.dumps(dummy_script)}

script_generation_agent = Agent(
    name="script_generation_agent",
    model="gemini-3-flash-preview",
    description=(
        "Analyzes transcript text and generates a structured educational script "
        "with segments, narrations, visual descriptions, and content_type classification "
        "('general' or 'maths')."
    ),
    instruction=(
        "You are a Script Generation Agent for educational reel videos. "
        "When given a transcript or topic text, use the generate_script tool to create "
        "a structured educational script. The tool will return a JSON script with segments. "
        "Return ONLY the raw JSON string from the tool's 'script' field as your final output. "
        "Do not add any extra commentary or formatting."
    ),
    tools=[generate_script],
    output_key="script_output",
)
