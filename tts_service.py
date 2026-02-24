"""
tts_service.py - Text-to-Speech service using gTTS (Google Text-to-Speech).

Converts slide script text into an MP3 audio file.
No API key needed — gTTS uses Google Translate's free TTS endpoint.
"""

from gtts import gTTS


def generate_audio(text: str, output_path: str) -> str:
    """
    Generate an MP3 audio file from the given text using gTTS.

    Args:
        text: The full script text to convert to speech.
        output_path: File path where the MP3 will be saved.

    Returns:
        The output_path on success.

    Raises:
        Exception: If gTTS fails to generate the audio.
    """
    print(f"[TTS] Generating audio ({len(text)} chars) -> {output_path}", flush=True)

    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_path)

    print(f"[TTS] Audio saved successfully: {output_path}", flush=True)
    return output_path
