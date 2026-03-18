"""
tasks.py - Background processing pipeline for file-to-video conversion.

Supports TWO modes:
    1. ADK Mode (default) — Uses Google ADK multi-agent pipeline
       Agents: Text Extraction → Script Generation → TTS → [Manim | Documentary] → DB
    2. Legacy Mode (fallback) — Direct function calls (original pipeline)
       Used when ADK is not installed or when USE_ADK=false in .env

Set USE_ADK=true/false in your .env to toggle between modes.
"""

import json
import os
import uuid
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from database import update_file_status, insert_video

load_dotenv()
USE_ADK = os.getenv("USE_ADK", "true").lower() in ("true", "1", "yes")

AUDIO_DIR = Path("audio")
VIDEOS_DIR = Path("videos")
IMAGES_DIR = Path("images")


# ============================================================================
# ADK Pipeline (Multi-Agent)
# ============================================================================

async def _run_adk_pipeline(file_id: int, filepath: str):
    """Run the ADK multi-agent pipeline."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from agents.agent import root_agent

    # Create session service and runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="microlearning",
        session_service=session_service,
    )

    # Create a session with initial state
    session = await session_service.create_session(
        app_name="microlearning",
        user_id="system",
        state={
            "filepath": filepath,
            "file_id": str(file_id),
        },
    )

    # Create user message to kick off the pipeline
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=f"Process file at {filepath} with file_id={file_id}")],
    )

    # Run the agent pipeline
    final_response = None
    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response():
            final_response = event.content.parts[0].text

    return final_response


def _process_file_adk(file_id: int, filepath: str, filename: str):
    """Process file using ADK multi-agent pipeline."""
    print(f"\n[ADK] ═══════════════════════════════════════════════", flush=True)
    print(f"[ADK] STARTED for file_id={file_id}: {filename}", flush=True)
    print(f"[ADK] Using multi-agent pipeline (Google ADK)", flush=True)
    print(f"[ADK] ═══════════════════════════════════════════════\n", flush=True)

    try:
        update_file_status(file_id, "processing")
        result = asyncio.run(_run_adk_pipeline(file_id, filepath))
        print(f"\n[ADK] ✓ COMPLETED for file_id={file_id}: {filename}", flush=True)
        print(f"[ADK] Result: {result}", flush=True)
    except Exception as e:
        print(f"\n[ADK] ✗ FATAL ERROR for file_id={file_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        update_file_status(file_id, "failed")


# ============================================================================
# Legacy Pipeline (Direct function calls — fallback)
# ============================================================================

def _process_file_legacy(file_id: int, filepath: str, filename: str):
    """Full processing pipeline using direct function calls (original approach)."""
    from text_extractor import extract_text
    from gemini_service import generate_script
    from tts_service import generate_per_slide_audio, concatenate_audio
    from image_service import generate_slide_images, generate_teacher
    from video_generator import generate_video

    print(f"\n[LEGACY] STARTED for file_id={file_id}: {filename}", flush=True)
    try:
        # --- Step 1: Extract text ---
        print(f"\nExtracting text...", flush=True)
        text = extract_text(filepath)
        if not text or not text.strip():
            print(f"FAILED: No text could be extracted.", flush=True)
            update_file_status(file_id, "failed")
            return
        print(f"Text extracted: {len(text)} characters.", flush=True)

        # --- Step 2: Generate script via Gemini ---
        print(f"\nGenerating script via Gemini...", flush=True)
        script = generate_script(text)

        if not script:
            print(f"FAILED: Gemini script generation returned None.", flush=True)
            update_file_status(file_id, "failed")
            return

        content_type = script.get("content_type", "general")
        script_json_str = json.dumps(script, ensure_ascii=False)
        update_file_status(file_id, "script_ready", script_json=script_json_str)
        print(f"Script saved: {len(script['slides'])} slides, type={content_type}.", flush=True)

        # --- Step 3: Generate TTS audio ---
        print(f"\nGenerating TTS audio (edge-tts)...", flush=True)

        audio_subdir = str(AUDIO_DIR / f"file_{file_id}_{uuid.uuid4().hex[:8]}")
        audio_results = generate_per_slide_audio(script["slides"], audio_subdir)

        slide_audio_paths = [path for path, _ in audio_results]
        slide_durations = [duration for _, duration in audio_results]

        combined_audio_filename = f"{uuid.uuid4().hex}.mp3"
        combined_audio_path = str(AUDIO_DIR / combined_audio_filename)
        concatenate_audio(slide_audio_paths, combined_audio_path)

        print(f"Audio ready. Durations: {[f'{d:.1f}s' for d in slide_durations]}", flush=True)

        # --- Step 4: Generate images (general content only) ---
        slide_images = None
        teacher_image = None

        if content_type == "general":
            print(f"\nGenerating AI images for documentary video...", flush=True)
            images_subdir = str(IMAGES_DIR / f"file_{file_id}_{uuid.uuid4().hex[:8]}")

            # Generate scene backgrounds
            slide_images = generate_slide_images(script["slides"], images_subdir)

            # Generate teacher character
            teacher_image = generate_teacher(images_subdir)

            successful = sum(1 for p in slide_images if p is not None)
            print(f"Images ready: {successful}/{len(script['slides'])} scenes, teacher={'✓' if teacher_image else '✗'}", flush=True)
        else:
            print(f"\nSkipping image generation (math content uses Manim).", flush=True)

        # --- Step 5: Generate video ---
        print(f"\nGenerating video ({content_type} pipeline)...", flush=True)

        video_filename = f"{uuid.uuid4().hex}.mp4"
        video_path = str(VIDEOS_DIR / video_filename)

        generate_video(
            slides=script["slides"],
            slide_durations=slide_durations,
            audio_path=combined_audio_path,
            output_path=video_path,
            content_type=content_type,
            slide_images=slide_images,
            teacher_image=teacher_image,
        )
        print(f"Video generated: {video_path}", flush=True)

        # --- Step 6: Update database ---
        insert_video(file_id, video_path, status="ready")
        update_file_status(file_id, "video_ready")

        print(f"COMPLETED for file_id={file_id}: {filename}", flush=True)

    except Exception as e:
        print(f"\nFATAL ERROR for file_id={file_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        update_file_status(file_id, "failed")


# ============================================================================
# Public API — Unified entry point
# ============================================================================

def process_file(file_id: int, filepath: str, filename: str):
    """Process an uploaded file through the video generation pipeline.

    Routes to ADK multi-agent pipeline or legacy direct calls based on
    the USE_ADK environment variable.
    """
    if USE_ADK:
        _process_file_adk(file_id, filepath, filename)
    else:
        _process_file_legacy(file_id, filepath, filename)
