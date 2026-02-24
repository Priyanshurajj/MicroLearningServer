"""
tts_service.py - Text-to-Speech service using Edge-TTS (Microsoft Neural TTS).

Generates natural-sounding per-slide audio clips for perfect sync with video.
No API key needed — uses Microsoft Edge's free neural TTS endpoint.

Voices: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
"""

import asyncio
import os
import uuid
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3


# ---------------------------------------------------------------------------
# TTS Configuration
# ---------------------------------------------------------------------------
VOICE = "en-US-AriaNeural"   # Natural female voice (change to en-US-GuyNeural for male)
RATE = "+0%"                  # Speech rate adjustment (e.g. "+10%", "-5%")
PITCH = "+0Hz"                # Pitch adjustment


async def _generate_single_clip(text: str, output_path: str) -> str:
    """
    Generate a single MP3 audio clip from text using Edge-TTS.
    """
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(output_path)
    return output_path


def _get_audio_duration(filepath: str) -> float:
    """
    Get the duration of an MP3 file in seconds using mutagen.
    No FFmpeg dependency required.
    """
    audio = MP3(filepath)
    return audio.info.length


def generate_per_slide_audio(slides: list, output_dir: str) -> list[tuple[str, float]]:
    """
    Generate individual audio clips for each slide and return their durations.

    Args:
        slides: List of slide dicts with 'title' and 'content' keys.
        output_dir: Directory to save the individual MP3 clips.

    Returns:
        List of (audio_path, duration_seconds) tuples, one per slide.
    """
    print(f"[TTS] Generating per-slide audio for {len(slides)} slides...", flush=True)
    print(f"[TTS] Voice: {VOICE}", flush=True)

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for i, slide in enumerate(slides):
        title = slide.get("title", "")
        content = slide.get("content", "")

        # Build narration text for this slide
        narration = f"{title}. {content}"

        # Generate unique filename
        clip_filename = f"slide_{i+1}_{uuid.uuid4().hex[:8]}.mp3"
        clip_path = os.path.join(output_dir, clip_filename)

        # Generate audio
        asyncio.run(_generate_single_clip(narration, clip_path))

        # Measure duration
        duration = _get_audio_duration(clip_path)
        results.append((clip_path, duration))

        print(f"[TTS]   Slide {i+1}/{len(slides)}: {duration:.1f}s - \"{title}\"", flush=True)

    total_duration = sum(d for _, d in results)
    print(f"[TTS] Total audio duration: {total_duration:.1f}s", flush=True)

    return results


def concatenate_audio(audio_files: list[str], output_path: str) -> str:
    """
    Concatenate multiple MP3 files into a single MP3 by binary concatenation.
    This works because all clips are generated with the same encoder settings.

    Args:
        audio_files: List of paths to MP3 files to concatenate (in order).
        output_path: Path for the combined output MP3.

    Returns:
        The output_path.
    """
    print(f"[TTS] Concatenating {len(audio_files)} audio clips...", flush=True)

    with open(output_path, "wb") as outfile:
        for path in audio_files:
            with open(path, "rb") as infile:
                outfile.write(infile.read())

    # Verify combined duration
    total_duration = _get_audio_duration(output_path)
    print(f"[TTS] Combined audio saved: {output_path} ({total_duration:.1f}s)", flush=True)
    return output_path
