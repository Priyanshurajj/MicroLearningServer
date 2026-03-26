import json
from google.adk.agents import Agent


def generate_script(transcript: str) -> dict:
    """
    Analyzes the transcript and generates a structured educational script.
    Each segment is tagged with segment_type: 'general' or 'maths'.
    """
    math_keywords = [
        "theorem", "equation", "formula", "calculate", "algebra",
        "geometry", "calculus", "derivative", "integral", "pythagorean",
        "quadratic", "polynomial", "trigonometry", "matrix", "vector",
        "proof", "axiom", "logarithm", "probability", "statistics",
        "a^2", "b^2", "c^2", "x^2", "f(x)", "sin", "cos", "tan",
    ]
    transcript_lower = transcript.lower()
    has_math = any(kw in transcript_lower for kw in math_keywords)

    dummy_script = {
        "title": f"Learn About: {transcript[:50]}...",
        "topic": transcript[:100],
        "segments": [
            {
                "segment_id": 1,
                "segment_type": "general",
                "narration": f"Welcome! Today we'll explore an interesting topic. {transcript[:80]}",
                "visual_description": "An engaging title card with the topic name displayed prominently with animated background",
                "duration_seconds": 5.0,
            },
            {
                "segment_id": 2,
                "segment_type": "maths" if has_math else "general",
                "narration": f"Let's dive deeper into the key concepts. {transcript[80:200] if len(transcript) > 80 else 'This is a fascinating subject with many applications.'}",
                "visual_description": "Illustrative diagram showing the main concept with labeled parts and arrows" if not has_math else "Mathematical derivation showing step-by-step proof with equations",
                "duration_seconds": 8.0,
                "math_expression": "a^2 + b^2 = c^2" if has_math else None,
            },
            {
                "segment_id": 3,
                "segment_type": "maths" if has_math else "general",
                "narration": "Here's a practical example to help you understand better. Notice how everything connects together.",
                "visual_description": "Real-world example visualization with step-by-step annotations" if not has_math else "Animated geometric visualization demonstrating the theorem",
                "duration_seconds": 7.0,
                "math_expression": "c = sqrt(a^2 + b^2)" if has_math else None,
            },
            {
                "segment_id": 4,
                "segment_type": "general",
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
        "with per-segment type tagging ('general' or 'maths')."
    ),
    instruction=(
        "You are a Script Generation Agent for educational reel videos. "
        "When given a transcript or topic text, use the generate_script tool. "
        "Return ONLY the raw JSON string from the tool's 'script' field as your output. "
        "Do not add any extra commentary or formatting."
    ),
    tools=[generate_script],
    output_key="script_output",
)
