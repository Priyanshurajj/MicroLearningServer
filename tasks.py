"""
tasks.py - Background task pipeline for the MicroLearningServer.

Full processing pipeline triggered after file upload:
    1. Extract text from uploaded file
    2. Generate micro-learning script via Gemini AI
    3. Generate TTS audio from the script
    4. Generate video from slides + audio
    5. Update database with results

Day 3: Added TTS + video generation stages to the pipeline.
"""

import json
import uuid
from pathlib import Path

from text_extractor import extract_text
from gemini_service import generate_script
from tts_service import generate_audio
from video_generator import generate_video
from database import update_file_status, insert_video

# ---------------------------------------------------------------------------
# Output directories (created at startup in main.py)
# ---------------------------------------------------------------------------
AUDIO_DIR = Path("audio")
VIDEOS_DIR = Path("videos")


def process_file(file_id: int, filepath: str, filename: str):
    """
    Full background processing pipeline for an uploaded file.

    Pipeline stages:
        1. Text extraction
        2. Gemini script generation
        3. TTS audio generation
        4. Video generation
        5. Database updates

    Args:
        file_id: Database ID of the uploaded file.
        filepath: Full path to the uploaded file on disk.
        filename: Original filename (used for naming outputs).
    """
    print(f"\n{'='*60}", flush=True)
    print(f"[PIPELINE] STARTED for file_id={file_id}: {filename}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        # ==================================================================
        # Stage 1: Extract text
        # ==================================================================
        print(f"\n[PIPELINE] Stage 1/4: Extracting text...", flush=True)
        text = extract_text(filepath)

        if not text or not text.strip():
            print(f"[PIPELINE] FAILED: No text could be extracted.", flush=True)
            update_file_status(file_id, "failed")
            return

        print(f"[PIPELINE] Text extracted: {len(text)} characters.", flush=True)

        # ==================================================================
        # Stage 2: Generate script via Gemini
        # ==================================================================
        print(f"\n[PIPELINE] Stage 2/4: Generating script via Gemini...", flush=True)
        script = generate_script(text)

        if not script:
            print(f"[PIPELINE] FAILED: Gemini script generation returned None.", flush=True)
            update_file_status(file_id, "failed")
            return

        # Save script to DB
        script_json_str = json.dumps(script, ensure_ascii=False)
        update_file_status(file_id, "script_ready", script_json=script_json_str)
        print(f"[PIPELINE] Script saved with {len(script['slides'])} slides.", flush=True)

        # ==================================================================
        # Stage 3: Generate TTS audio
        # ==================================================================
        print(f"\n[PIPELINE] Stage 3/4: Generating TTS audio...", flush=True)

        # Combine all slide content into one script for narration
        full_narration = ". ".join(
            f"{slide['title']}. {slide['content']}"
            for slide in script["slides"]
        )

        # Generate unique audio filename
        audio_filename = f"{uuid.uuid4().hex}.mp3"
        audio_path = str(AUDIO_DIR / audio_filename)

        generate_audio(full_narration, audio_path)
        print(f"[PIPELINE] Audio generated: {audio_path}", flush=True)

        # ==================================================================
        # Stage 4: Generate video
        # ==================================================================
        print(f"\n[PIPELINE] Stage 4/4: Generating video...", flush=True)

        # Generate unique video filename
        video_filename = f"{uuid.uuid4().hex}.mp4"
        video_path = str(VIDEOS_DIR / video_filename)

        generate_video(script["slides"], audio_path, video_path)
        print(f"[PIPELINE] Video generated: {video_path}", flush=True)

        # ==================================================================
        # Final: Update database
        # ==================================================================
        insert_video(file_id, video_path, status="ready")
        update_file_status(file_id, "video_ready")

        print(f"\n{'='*60}", flush=True)
        print(f"[PIPELINE] COMPLETED for file_id={file_id}: {filename}", flush=True)
        print(f"{'='*60}\n", flush=True)

    except Exception as e:
        print(f"\n[PIPELINE] FATAL ERROR for file_id={file_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        update_file_status(file_id, "failed")
