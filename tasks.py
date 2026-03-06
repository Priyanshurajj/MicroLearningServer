import json
import uuid
from pathlib import Path

from text_extractor import extract_text
from gemini_service import generate_script
from tts_service import generate_per_slide_audio, concatenate_audio
from video_generator import generate_video
from database import update_file_status, insert_video

AUDIO_DIR = Path("audio")
VIDEOS_DIR = Path("videos")

def process_file(file_id: int, filepath: str, filename: str):
    print(f"STARTED for file_id={file_id}: {filename}", flush=True)
    try:
        print(f"\nExtracting text...", flush=True)
        text = extract_text(filepath)
        if not text or not text.strip():
            print(f"FAILED: No text could be extracted.", flush=True)
            update_file_status(file_id, "failed")
            return
        print(f"Text extracted: {len(text)} characters.", flush=True)


        print(f"\nGenerating script via Gemini...", flush=True)
        script = generate_script(text)

        if not script:
            print(f"FAILED: Gemini script generation returned None.", flush=True)
            update_file_status(file_id, "failed")
            return

        script_json_str = json.dumps(script, ensure_ascii=False)
        update_file_status(file_id, "script_ready", script_json=script_json_str)
        print(f"Script saved with {len(script['slides'])} slides.", flush=True)

        print(f"\nGenerating TTS audio (edge-tts)...", flush=True)

        audio_subdir = str(AUDIO_DIR / f"file_{file_id}_{uuid.uuid4().hex[:8]}")

        audio_results = generate_per_slide_audio(script["slides"], audio_subdir)

        slide_audio_paths = [path for path, _ in audio_results]
        slide_durations = [duration for _, duration in audio_results]

        combined_audio_filename = f"{uuid.uuid4().hex}.mp3"
        combined_audio_path = str(AUDIO_DIR / combined_audio_filename)
        concatenate_audio(slide_audio_paths, combined_audio_path)

        print(f"Audio ready. Slide durations: {[f'{d:.1f}s' for d in slide_durations]}", flush=True)

        print(f"\nGenerating Manim video...", flush=True)

        video_filename = f"{uuid.uuid4().hex}.mp4"
        video_path = str(VIDEOS_DIR / video_filename)

        generate_video(script["slides"], slide_durations, combined_audio_path, video_path)
        print(f"Video generated: {video_path}", flush=True)

        insert_video(file_id, video_path, status="ready")
        update_file_status(file_id, "video_ready")

        print(f"COMPLETED for file_id={file_id}: {filename}", flush=True)
  
    except Exception as e:
        print(f"\nFATAL ERROR for file_id={file_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        update_file_status(file_id, "failed")
