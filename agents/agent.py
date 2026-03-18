"""
MicroLearning Multi-Agent Pipeline using Google ADK.

Architecture:
    Common:  Text Extraction → Script Generation → TTS
    Math:    → Manim Video Agent → DB
    General: → (Image Gen) → Documentary Video Agent → DB

The root_agent (LLM) dynamically routes to the correct video pipeline
based on the content_type decided by the Script Agent.
"""

import json
import uuid
import tempfile
from pathlib import Path

from google.adk.agents import Agent, SequentialAgent

# ─── Import existing services (UNCHANGED) ───
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from text_extractor import extract_text as _extract_text
from tts_service import generate_per_slide_audio, concatenate_audio
from image_service import generate_slide_images, generate_teacher
from video_generator import (
    generate_documentary_video,   # Documentary pipeline
    _render_manim_scene,          # Manim rendering
    _compose_audio,               # Audio compositing
)
from database import update_file_status, insert_video


# ============================================================================
# TOOL FUNCTIONS (Wrapped as FunctionTools by ADK)
# ============================================================================

# ── Text Extraction Tool ──
def extract_text_tool(filepath: str) -> dict:
    """Extract text content from an uploaded file.

    Args:
        filepath: Absolute path to the uploaded .txt or .pdf file.

    Returns:
        dict with 'status' and 'text' keys.
    """
    try:
        text = _extract_text(filepath)
        if not text or not text.strip():
            return {"status": "error", "error_message": "No text could be extracted."}
        return {"status": "success", "text": text}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ── TTS Tool ──
def generate_tts_tool(script_json: str, file_id: str) -> dict:
    """Generate text-to-speech audio for all slides.

    Args:
        script_json: JSON string of the script with slides array.
        file_id: Unique file identifier for organizing audio files.

    Returns:
        dict with audio_paths, slide_durations, and combined_audio_path.
    """
    try:
        script = json.loads(script_json)
        slides = script["slides"]

        audio_dir = Path("audio")
        audio_subdir = str(audio_dir / f"file_{file_id}_{uuid.uuid4().hex[:8]}")

        audio_results = generate_per_slide_audio(slides, audio_subdir)
        slide_audio_paths = [path for path, _ in audio_results]
        slide_durations = [duration for _, duration in audio_results]

        combined_audio_path = str(audio_dir / f"{uuid.uuid4().hex}.mp3")
        concatenate_audio(slide_audio_paths, combined_audio_path)

        return {
            "status": "success",
            "audio_paths": slide_audio_paths,
            "slide_durations": slide_durations,
            "combined_audio_path": combined_audio_path,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ── Image Generation Tool (Documentary only) ──
def generate_images_tool(script_json: str, file_id: str) -> dict:
    """Generate AI background images and teacher character for documentary video.

    Args:
        script_json: JSON string of the script with slides array.
        file_id: Unique file identifier for organizing image files.

    Returns:
        dict with slide_images list and teacher_image path.
    """
    try:
        script = json.loads(script_json)
        slides = script["slides"]
        images_dir = Path("images")
        images_subdir = str(images_dir / f"file_{file_id}_{uuid.uuid4().hex[:8]}")

        slide_images = generate_slide_images(slides, images_subdir)
        teacher_image = generate_teacher(images_subdir)

        return {
            "status": "success",
            "slide_images": slide_images,
            "teacher_image": teacher_image,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ── 📐 Manim Video Tool ──
def generate_manim_video_tool(
    script_json: str,
    slide_durations_json: str,
    combined_audio_path: str,
) -> dict:
    """Generate an animated math video using Manim Community Edition.

    Creates animated scenes with equations, diagrams, and text animations.
    Best suited for mathematical, scientific, and formula-heavy content.

    Args:
        script_json: JSON string of the script data with slides.
        slide_durations_json: JSON array of per-slide durations in seconds.
        combined_audio_path: Path to the combined narration audio file.

    Returns:
        dict with the generated video file path.
    """
    try:
        script = json.loads(script_json)
        slide_durations = json.loads(slide_durations_json)

        video_filename = f"{uuid.uuid4().hex}.mp4"
        video_path = str(Path("videos") / video_filename)
        temp_dir = tempfile.mkdtemp(prefix="manim_render_")

        # Render Manim scenes (animated math content)
        silent_video = _render_manim_scene(
            slides=script["slides"],
            slide_durations=slide_durations,
            temp_dir=temp_dir,
        )

        # Compose audio onto silent video
        _compose_audio(silent_video, combined_audio_path, video_path)

        return {"status": "success", "video_path": video_path}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ── 🎨 Documentary Video Tool ──
def generate_documentary_video_tool(
    script_json: str,
    slide_durations_json: str,
    combined_audio_path: str,
    slide_images_json: str,
    teacher_image: str,
) -> dict:
    """Generate a cinematic documentary-style video with AI images.

    Creates videos with AI-generated backgrounds, Ken Burns zoom effect,
    teacher character overlay, gradient text cards, and smooth transitions.
    Best suited for general, non-mathematical educational content.

    Args:
        script_json: JSON string of the script data with slides.
        slide_durations_json: JSON array of per-slide durations in seconds.
        combined_audio_path: Path to the combined narration audio file.
        slide_images_json: JSON array of background image paths per slide.
        teacher_image: Path to teacher character image (or empty string).

    Returns:
        dict with the generated video file path.
    """
    try:
        script = json.loads(script_json)
        slide_durations = json.loads(slide_durations_json)
        slide_images = json.loads(slide_images_json) if slide_images_json else []

        video_filename = f"{uuid.uuid4().hex}.mp4"
        video_path = str(Path("videos") / video_filename)

        generate_documentary_video(
            slides=script["slides"],
            slide_images=slide_images if slide_images else [None] * len(script["slides"]),
            teacher_image=teacher_image if teacher_image else None,
            slide_durations=slide_durations,
            audio_path=combined_audio_path,
            output_path=video_path,
        )

        return {"status": "success", "video_path": video_path}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ── Database Tool ──
def save_to_database_tool(file_id: str, video_path: str) -> dict:
    """Save the generated video record to the database.

    Args:
        file_id: The database file ID.
        video_path: Path to the generated video file.

    Returns:
        dict confirming the save status.
    """
    try:
        file_id_int = int(file_id)
        insert_video(file_id_int, video_path, status="ready")
        update_file_status(file_id_int, "video_ready")
        return {"status": "success", "message": f"Video saved for file_id={file_id}"}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

# ── Agent 1: Text Extraction ──
text_extraction_agent = Agent(
    name="text_extraction_agent",
    model="gemini-2.0-flash",
    description="Extracts text from uploaded files (.txt or .pdf).",
    instruction="""You are a text extraction specialist.

Given a filepath at: {filepath}

Use the extract_text_tool to extract the text content from the file.
Return the extracted text content. If extraction fails, explain the error.""",
    tools=[extract_text_tool],
    output_key="raw_text",
)

# ── Agent 2: Script Generation ──
script_generation_agent = Agent(
    name="script_generation_agent",
    model="gemini-2.5-flash",
    description="Generates structured micro-learning scripts from text content.",
    instruction="""You are an educational content creator specializing in micro-learning.

Given the following extracted text: {raw_text}

Create a 60-second micro-learning script. Return ONLY a valid JSON object (no markdown) with:
{
    "summary": "2-3 line summary",
    "content_type": "general" or "math",
    "slides": [
        {
            "title": "Slide Title",
            "content": "2-3 lines of educational content",
            "image_prompt": "Detailed visual description for AI image generation",
            "scene_mood": "bright|dark|warm|cool|energetic|calm|dramatic|playful"
        }
    ]
}

Rules:
- Set content_type to "math" ONLY for math/equations/formulas content.
- 5-7 slides total, each with clear title and 2-3 lines of content.
- image_prompt should describe vivid scenes with NO text in the image.
- Return ONLY the JSON object.""",
    output_key="script_data",
)

# ── Agent 3: TTS Audio Generation (shared by both pipelines) ──
tts_agent = Agent(
    name="tts_agent",
    model="gemini-2.0-flash",
    description="Generates text-to-speech audio for script slides.",
    instruction="""You are a TTS audio specialist.

Use the generate_tts_tool with:
- script_json: {script_data}
- file_id: {file_id}

Generate audio narration for all slides.
Report the results including durations for each slide.""",
    tools=[generate_tts_tool],
    output_key="tts_result",
)

# ── Agent 4: Image Generation (Documentary pipeline only) ──
image_agent = Agent(
    name="image_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates AI background images and teacher character for documentary video. "
        "Only used for general (non-math) content."
    ),
    instruction="""You are an image generation specialist for documentary-style videos.

Use the generate_images_tool with:
- script_json: {script_data}
- file_id: {file_id}

Generate background images for each slide and a teacher character image.
Report results including how many images were successfully generated.""",
    tools=[generate_images_tool],
    output_key="image_result",
)

# ── Agent 5: 📐 Manim Video Agent (Math content) ──
manim_video_agent = Agent(
    name="manim_video_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates animated math videos using Manim. Handles mathematical "
        "content with equations, formulas, and animated diagrams."
    ),
    instruction="""You are a MANIM VIDEO specialist for mathematical educational content.

You create animated math videos with equations, diagrams, and text animations
using Manim Community Edition.

Use the generate_manim_video_tool with:
- script_json: {script_data}
- slide_durations_json: extract the slide_durations array from {tts_result}
- combined_audio_path: extract the combined_audio_path from {tts_result}

Generate the animated math video and report the output path.""",
    tools=[generate_manim_video_tool],
    output_key="video_result",
)

# ── Agent 6: 🎨 Documentary Video Agent (General content) ──
documentary_video_agent = Agent(
    name="documentary_video_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates cinematic documentary-style videos with AI images, "
        "Ken Burns effect, and teacher overlay. Handles general (non-math) content."
    ),
    instruction="""You are a DOCUMENTARY VIDEO specialist for general educational content.

You create cinematic videos with AI-generated backgrounds, Ken Burns zoom effects,
teacher character overlays, and smooth transitions.

Use the generate_documentary_video_tool with:
- script_json: {script_data}
- slide_durations_json: extract the slide_durations array from {tts_result}
- combined_audio_path: extract the combined_audio_path from {tts_result}
- slide_images_json: extract the slide_images array from {image_result}
- teacher_image: extract the teacher_image path from {image_result}

Generate the documentary video and report the output path.""",
    tools=[generate_documentary_video_tool],
    output_key="video_result",
)

# ── DB Agent helper (creates a unique agent per pipeline) ──
_DB_AGENT_INSTRUCTION = """You are a database specialist.

Use the save_to_database_tool with:
- file_id: {file_id}
- video_path: extract the video_path from {video_result}

Save the video record and confirm the status."""


def _make_db_agent(name: str) -> Agent:
    """Create a DB agent instance. ADK requires each agent to have a single parent,
    so we create one per pipeline."""
    return Agent(
        name=name,
        model="gemini-2.0-flash",
        description="Saves video records to the database.",
        instruction=_DB_AGENT_INSTRUCTION,
        tools=[save_to_database_tool],
        output_key="db_result",
    )


# ============================================================================
# PIPELINE: Common Steps (Text → Script → TTS)
# ============================================================================

common_pipeline = SequentialAgent(
    name="common_pipeline",
    description="Runs the common first steps: text extraction, script generation, and TTS.",
    sub_agents=[
        text_extraction_agent,     # Step 1: Extract text from file
        script_generation_agent,   # Step 2: Generate script via Gemini
        tts_agent,                 # Step 3: Generate TTS audio
    ],
)


# ============================================================================
# PIPELINE: Manim (Math content)
# ============================================================================

manim_pipeline = SequentialAgent(
    name="manim_pipeline",
    description=(
        "Manim video pipeline for math content. "
        "Renders animated scenes with equations and formulas."
    ),
    sub_agents=[
        manim_video_agent,              # Render Manim animated scenes
        _make_db_agent("manim_db"),     # Save to database
    ],
)


# ============================================================================
# PIPELINE: Documentary (General content)
# ============================================================================

documentary_pipeline = SequentialAgent(
    name="documentary_pipeline",
    description=(
        "Documentary video pipeline for general content. Generates AI images, "
        "then creates cinematic video with Ken Burns effect and teacher overlay."
    ),
    sub_agents=[
        image_agent,                         # Generate AI backgrounds + teacher
        documentary_video_agent,             # Render documentary video
        _make_db_agent("documentary_db"),    # Save to database
    ],
)


# ============================================================================
# ROOT AGENT (Entry point — LLM-powered Router)
# ============================================================================

root_agent = Agent(
    name="microlearning_orchestrator",
    model="gemini-2.0-flash",
    description=(
        "Orchestrates the full micro-learning video generation pipeline. "
        "Routes to Manim or Documentary pipeline based on content type."
    ),
    instruction="""You are the MicroLearning Orchestrator.

You manage the complete video generation pipeline for educational content.

The file information is:
- filepath: {filepath}
- file_id: {file_id}

Follow these steps:

1. FIRST: Delegate to `common_pipeline` to run text extraction, script generation, and TTS audio.

2. THEN: Check the content_type from the generated script in {script_data}:
   - If content_type is "math" → delegate to `manim_pipeline`
     (creates animated math videos with Manim)
   - If content_type is "general" → delegate to `documentary_pipeline`
     (generates AI images, then creates cinematic video with Ken Burns effect)

3. Report the final status after the video is generated and saved to the database.""",
    sub_agents=[common_pipeline, manim_pipeline, documentary_pipeline],
)
