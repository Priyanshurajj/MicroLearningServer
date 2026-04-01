from google.adk.agents import SequentialAgent, ParallelAgent

from .hook_agent import hook_agent
from .script_generation_agent import script_agent
from .script_review_agent import script_review_agent
from .creative_director_agent import creative_director_agent
from .prompt_review_agent import prompt_review_agent
from .tts_agent import tts_agent
from .image_agent import image_agent
from .manim_code_agent import manim_code_agent
from .manim_qc_agent import manim_qc_agent
from .concept_map_agent import concept_map_agent
from .video_editor_agent import video_editor_agent

# ── Parallel Asset Generation ──
# TTS, image generation, and Manim code generation all read from enhanced_script
# and write to separate state keys — safe to run fully in parallel.
asset_generator = ParallelAgent(
    name="asset_generator",
    description=(
        "Runs TTS audio generation, image generation (Imagen), and Manim code generation "
        "in parallel. All three agents read from enhanced_script in session state."
    ),
    sub_agents=[tts_agent, image_agent, manim_code_agent],
)

# ── Full Pipeline ──
root_agent = SequentialAgent(
    name="root_agent",
    description="Complete EduReel content creation pipeline.",
    sub_agents=[
        hook_agent,               # 2. Generate curiosity hook opening segment
        script_agent,             # 3. Generate structured script (uses narrative_transcript + hook_segment)
        script_review_agent,      # 4. Validate & repair script JSON
        creative_director_agent,  # 5. Enhance visual prompts (cinematic + manim_spec)
        prompt_review_agent,      # 6. Safety-check image prompts & manim_spec
        asset_generator,          # 7. Parallel: TTS + images + Manim code
        manim_qc_agent,           # 8. Execute & auto-heal Manim code, attach bg images
        concept_map_agent,        # 9. Generate per-segment concept map overlay PNGs
        video_editor_agent,       # 10. Compose final reel video
    ],
)
