import asyncio
import os
import uuid
from pathlib import Path
import edge_tts
from mutagen.mp3 import MP3

VOICE = "en-US-AriaNeural"   # Natural female voice (change to en-US-GuyNeural for male)
RATE = "+0%"                  # Speech rate adjustment (e.g. "+10%", "-5%")
PITCH = "+0Hz"                # Pitch adjustment

async def _generate_single_clip(text: str, output_path: str) -> str:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(output_path)
    return output_path

def _get_audio_duration(filepath: str) -> float:
    audio = MP3(filepath)
    return audio.info.length

def generate_per_slide_audio(slides: list, output_dir: str) -> list[tuple[str, float]]:
    print(f"Generating per-slide audio for {len(slides)} slides", flush=True)
    print(f"Voice: {VOICE}", flush=True)

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for i, slide in enumerate(slides):
        title = slide.get("title", "")
        content = slide.get("content", "")

        narration = f"{title}. {content}"

        clip_filename = f"slide_{i+1}_{uuid.uuid4().hex[:8]}.mp3"
        clip_path = os.path.join(output_dir, clip_filename)

        asyncio.run(_generate_single_clip(narration, clip_path))

        duration = _get_audio_duration(clip_path)
        results.append((clip_path, duration))

        print(f"Slide {i+1}/{len(slides)}: {duration:.1f}s - \"{title}\"", flush=True)

    total_duration = sum(d for _, d in results)
    print(f"Total audio duration: {total_duration:.1f}s", flush=True)

    return results


def concatenate_audio(audio_files: list[str], output_path: str) -> str:
    print(f"Concatenating {len(audio_files)} audio clips", flush=True)

    with open(output_path, "wb") as outfile:
        for path in audio_files:
            with open(path, "rb") as infile:
                outfile.write(infile.read())

    total_duration = _get_audio_duration(output_path)
    print(f"Combined audio saved: {output_path} ({total_duration:.1f}s)", flush=True)
    return output_path
