from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from .script_generation_agent import generate_script
from .creative_director_agent import creative_director_agent
from .tts_agent import tts_agent
from .visual_asset_agent import visual_asset_agent
from .manim_qc_agent import manim_qc_agent
from .video_editor_agent import video_editor_agent


parallel_asset_generator = ParallelAgent(
    name="parallel_asset_generator",
    description=(
        "Runs TTS generation and visual asset generation in parallel. "
        "Both agents read from 'enhanced_script' in session state and write "
        "their outputs to 'tts_output' and 'visual_output' respectively."
    ),
    sub_agents=[tts_agent, visual_asset_agent],
)

master_pipeline = SequentialAgent(
    name="master_pipeline",
    description=(
        "The full content creation pipeline: "
        "Creative Director → Parallel(TTS + Visuals) → Manim QC → Video Editor"
    ),
    sub_agents=[
        creative_director_agent,   # Step 2: Enhance visual prompts
        parallel_asset_generator,  # Step 3: Generate TTS + images/manim code in parallel
        manim_qc_agent,            # Step 4: Validate and render Manim clips
        video_editor_agent,        # Step 5: Compose final mixed video
    ],
)

root_agent = Agent(
    name="root_agent",
    model="gemini-3-flash-preview",
    description=(
        "Director Agent for the EduReel video generation pipeline. "
        "Generates a script via tool call, then transfers to the master pipeline."
    ),
    instruction="""You are the Director Agent for the EduReel educational video generation system.

    STEP 1: Call the `generate_script` tool with the user's transcript.
    - The tool returns a JSON object with a "script" field.

    STEP 2: Transfer to `master_pipeline` to process the script through the full pipeline.
    - The pipeline will automatically handle: creative enhancement, TTS, image/Manim generation, QC, and final video composition.

    RULES:
    - ALWAYS call generate_script first as a tool.
    - ALWAYS transfer to master_pipeline after getting the script. Never return the script as your final answer.
    - The master_pipeline handles everything else automatically.
    """,
    tools=[generate_script],
    output_key="script_output",
    sub_agents=[master_pipeline],
)
