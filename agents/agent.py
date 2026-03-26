"""
EduReel ADK Pipeline — Root Orchestrator

Architecture: SequentialAgent root (no LLM routing overhead).
Every video goes through the same pipeline; mixed general + maths
segments are handled per-segment by each agent.

Pipeline:
  script_agent → creative_director → (TTS || Visuals) → Manim QC → Video Editor
"""
from google.adk.agents import SequentialAgent, ParallelAgent

from .script_generation_agent import script_agent
from .creative_director_agent import creative_director_agent
from .tts_agent import tts_agent
from .visual_asset_agent import visual_asset_agent
from .manim_qc_agent import manim_qc_agent
from .video_editor_agent import video_editor_agent

# ── Parallel Asset Generation (TTS + Visuals run simultaneously) ──
# Vertex AI has high rate limits, so ParallelAgent is safe.
# If on free-tier API, switch to SequentialAgent.
asset_generator = ParallelAgent(
    name="asset_generator",
    description=(
        "Runs TTS audio generation and visual asset generation in parallel. "
        "Both agents read the enhanced script from session state."
    ),
    sub_agents=[tts_agent, visual_asset_agent],
)

# ── Full Pipeline ──
root_agent = SequentialAgent(
    name="root_agent",
    description="Complete EduReel content creation pipeline.",
    sub_agents=[
        script_agent,              # 1. Generate structured script from transcript
        creative_director_agent,   # 2. Enhance visual prompts for Imagen & Manim
        asset_generator,           # 3. Generate TTS audio + images/Manim code (parallel)
        manim_qc_agent,            # 4. Execute & auto-heal Manim code
        video_editor_agent,        # 5. Compose final reel video
    ],
)
