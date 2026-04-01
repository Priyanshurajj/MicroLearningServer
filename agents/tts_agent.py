import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from moviepy import AudioFileClip

from .config import ROUTING_MODEL, OUTPUT_DIR, USE_CLOUD_TTS

logger = logging.getLogger("EduReelADK")


def _synthesize_segment_cloud_tts(narration: str, output_path: str) -> float:
    """Uses Google Cloud Text-to-Speech (Neural2) to generate audio. Returns duration."""
    from google.cloud import texttospeech  # type: ignore

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=narration)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-J",
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=0.95,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    audio_clip = AudioFileClip(output_path)
    duration = audio_clip.duration
    audio_clip.close()
    return duration


def _synthesize_segment_gtts(narration: str, output_path: str) -> float:
    """Uses gTTS to generate audio. Returns duration."""
    from gtts import gTTS  # type: ignore

    tts = gTTS(text=narration, lang="en", slow=False)
    tts.save(output_path)

    audio_clip = AudioFileClip(output_path)
    duration = audio_clip.duration
    audio_clip.close()
    return duration


def _synthesize_segment(seg: dict, audio_dir: str) -> dict:
    """Generates TTS audio for one segment. Returns audio metadata dict."""
    seg_id = seg["segment_id"]
    narration = seg.get("narration", "")
    output_path = os.path.join(audio_dir, f"segment_{seg_id}.mp3")

    try:
        if USE_CLOUD_TTS:
            try:
                duration = _synthesize_segment_cloud_tts(narration, output_path)
                logger.info(f"TTS (Cloud) segment {seg_id}: {duration:.1f}s")
            except Exception as cloud_err:
                logger.warning(
                    f"Cloud TTS failed for segment {seg_id}: {cloud_err}. Falling back to gTTS."
                )
                duration = _synthesize_segment_gtts(narration, output_path)
                logger.info(f"TTS (gTTS fallback) segment {seg_id}: {duration:.1f}s")
        else:
            duration = _synthesize_segment_gtts(narration, output_path)
            logger.info(f"TTS (gTTS) segment {seg_id}: {duration:.1f}s")

        return {
            "segment_id": seg_id,
            "audio_file_path": os.path.abspath(output_path),
            "duration_seconds": round(duration, 2),
            "narration_preview": narration[:80],
        }

    except Exception as e:
        logger.error(f"TTS failed for segment {seg_id}: {e}")
        return {
            "segment_id": seg_id,
            "audio_file_path": "",
            "duration_seconds": seg.get("duration_seconds", 5.0),
            "error": str(e),
        }


def generate_tts_audio(tool_context: ToolContext) -> dict:
    """Reads enhanced_script from session state and generates TTS audio for all segments."""
    script_json = tool_context.state.get("enhanced_script", "")
    if not script_json:
        script_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(script_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"TTS: Cannot parse script from state: {e}")
        return {"status": "error", "error": f"Cannot parse script from state: {e}"}

    run_id = script.get("run_id", "default")
    audio_dir = os.path.join(OUTPUT_DIR, run_id, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    segments = script.get("segments", [])
    audio_segments = []

    with ThreadPoolExecutor(max_workers=min(len(segments), 5)) as executor:
        futures = {
            executor.submit(_synthesize_segment, seg, audio_dir): seg
            for seg in segments
        }
        for future in as_completed(futures):
            audio_segments.append(future.result())

    # Sort by segment_id for deterministic output
    audio_segments.sort(key=lambda x: x["segment_id"])

    tts_result = {
        "run_id": run_id,
        "audio_segments": audio_segments,
        "total_duration_seconds": round(
            sum(s["duration_seconds"] for s in audio_segments), 2
        ),
        "segments_processed": len(audio_segments),
        "tts_backend": "cloud" if USE_CLOUD_TTS else "gtts",
    }

    logger.info(
        f"TTS complete: {len(audio_segments)} segments, "
        f"total {tts_result['total_duration_seconds']}s "
        f"(backend: {tts_result['tts_backend']})"
    )

    tts_output_json = json.dumps(tts_result)
    tool_context.state["tts_output"] = tts_output_json
    return {"status": "success", "tts_output": tts_output_json}


tts_agent = Agent(
    name="tts_agent",
    model=ROUTING_MODEL,
    description="Generates text-to-speech audio narration for all segments in parallel.",
    instruction=(
        "You are the TTS Agent. "
        "Call the generate_tts_audio tool immediately — it reads all data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_tts_audio],
)
