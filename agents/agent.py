from google.adk.agents import SequentialAgent, ParallelAgent

from .script_generation_agent import script_agent
from .script_review_agent import script_review_agent
from .creative_director_agent import creative_director_agent
from .prompt_review_agent import prompt_review_agent
from .tts_agent import tts_agent
from .image_agent import image_agent
from .manim_code_agent import manim_code_agent
from .manim_bg_image_agent import manim_bg_image_agent
from .manim_qc_agent import manim_qc_agent
from .concept_map_agent import concept_map_agent
from .video_editor_agent import video_editor_agent

# General: cinematic image per segment → image_output
general_pipeline = SequentialAgent(
    name="general_pipeline",
    description="Generates photorealistic Imagen images for all general-type segments.",
    sub_agents=[image_agent],
)

# Manim prep: code generation and background image generation are independent
# so they run in parallel, then manim_qc_agent renders/heals the code.
manim_prep = ParallelAgent(
    name="manim_prep",
    description=(
        "Generates Manim animation code (manim_code_agent) and optional cinematic "
        "background images (manim_bg_image_agent) concurrently. "
        "Both write to distinct state keys: manim_code_output, bg_image_output."
    ),
    sub_agents=[manim_code_agent, manim_bg_image_agent],
)

# Manim: prep → QC/render → qc_output (with bg_image_path attached per asset)
manim_pipeline = SequentialAgent(
    name="manim_pipeline",
    description=(
        "Full manim asset lifecycle. manim_prep runs in parallel, then "
        "manim_qc_agent renders the code and attaches background image paths."
    ),
    sub_agents=[manim_prep, manim_qc_agent],
)

# ─────────────────────────────────────────────
# Content Pipeline
# ─────────────────────────────────────────────
# TTS is type-agnostic (every segment has narration) so it runs alongside
# the type pipelines. All three write to distinct state keys — no conflicts.
content_pipeline = ParallelAgent(
    name="content_pipeline",
    description=(
        "Runs TTS audio generation, general image generation, and the full manim "
        "asset pipeline concurrently. "
        "State keys written: tts_output | image_output | manim_code_output, bg_image_output, qc_output"
    ),
    sub_agents=[tts_agent, general_pipeline, manim_pipeline],
)

# ─────────────────────────────────────────────
# Root Pipeline
# ─────────────────────────────────────────────
root_agent = SequentialAgent(
    name="root_agent",
    description="Complete EduReel content creation pipeline.",
    sub_agents=[
        script_agent,             # 1. Generate structured script from transcript
        script_review_agent,      # 2. Validate & repair script JSON
        creative_director_agent,  # 3. Enhance prompts: cinematic images + manim_spec + text_overlay
        prompt_review_agent,      # 4. Safety-check all image prompts and manim_spec fields
        content_pipeline,         # 5. Parallel: TTS | general assets | manim assets+QC
        concept_map_agent,        # 6. Generate per-segment concept map overlay PNGs
        video_editor_agent,       # 7. Compose final reel video
    ],
)
