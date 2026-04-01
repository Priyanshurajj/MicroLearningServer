"""
Shared configuration: google-genai client and model constants.
All tool functions import from here for consistent Vertex AI access.
"""
import os
import logging
from google import genai

logger = logging.getLogger("EduReelADK")

# ── Vertex AI Client ──
# Lazy-initialized to avoid import-time crash if credentials aren't set up yet.
_client = None


def get_client() -> genai.Client:
    """Returns a cached Vertex AI genai client. Created on first call."""
    global _client
    if _client is None:
        use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").upper() in ("TRUE", "1")

        if use_vertex:
            _client = genai.Client(
                vertexai=True,
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
            logger.info(
                f"genai client initialized (Vertex AI) "
                f"project={os.getenv('GOOGLE_CLOUD_PROJECT')}"
            )
        else:
            _client = genai.Client(
                api_key=os.getenv("GOOGLE_API_KEY"),
            )
            logger.info("genai client initialized (API Key mode)")

    return _client


# ── Model Constants ──
# ADK agent routing — fast, cheap, just decides which tool to call
ROUTING_MODEL = "gemini-2.5-flash"

# Script + creative work — good reasoning + fast
TEXT_MODEL = "gemini-2.5-flash"

# Manim code generation — best code accuracy, fewest errors
CODE_MODEL = "gemini-2.5-pro"

# Image generation
IMAGEN_MODEL = "imagen-3.0-generate-002"

# ── Output Directory ──
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# ── Text Overlay Font ──
# Set OVERLAY_FONT_PATH to a .ttf path if arial.ttf is not in the system font path.
OVERLAY_FONT_PATH = os.getenv("OVERLAY_FONT_PATH", "arial.ttf")

# ── Cloud TTS Toggle ──
# Set USE_CLOUD_TTS=true to use Google Cloud Text-to-Speech (Neural2 voices).
# Falls back to gTTS when false or when google-cloud-texttospeech is not installed.
USE_CLOUD_TTS = os.getenv("USE_CLOUD_TTS", "false").lower() in ("true", "1")
