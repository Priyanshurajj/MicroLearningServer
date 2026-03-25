from google.adk.agents import Agent, SequentialAgent
from .script_generation_agent import generate_script
from .tts_agent import tts_agent_general, tts_agent_maths
from .image_generation_agent import image_agent_general, image_agent_maths
from .video_generation_agent import video_generation_agent
from .manim_video_generation_agent import manim_video_generation_agent

general_pipeline = SequentialAgent(
    name="general_pipeline",
    description=(
        "Sequential pipeline for GENERAL educational content. "
        "Runs: TTS → Image Generation → Video Generation. "
        "Use this when content_type is 'general'."
    ),
    sub_agents=[tts_agent_general, image_agent_general, video_generation_agent],
)

maths_pipeline = SequentialAgent(
    name="maths_pipeline",
    description=(
        "Sequential pipeline for MATHEMATICAL educational content. "
        "Runs: TTS → Image Generation → Manim Video Generation. "
        "Use this when content_type is 'maths'."
    ),
    sub_agents=[tts_agent_maths, image_agent_maths, manim_video_generation_agent],
)

root_agent = Agent(
    name="root_agent",
    model="gemini-3-flash-preview",
    description=(
        "Root orchestrator for the EduReel video generation pipeline. "
        "Generates a script via tool, then routes to the appropriate pipeline."
    ),
    instruction="""You are the Root Orchestrator for the EduReel educational video generation system.

STEP 1: Call the `generate_script` tool with the user's transcript.
  - The tool returns a JSON object with a "script" field.
  - Parse the "script" JSON and find the "content_type" field.

STEP 2: Based on content_type, transfer to the correct pipeline:
  - If content_type is "general" → transfer to `general_pipeline`
  - If content_type is "maths" → transfer to `maths_pipeline`

RULES:
- ALWAYS call generate_script first as a tool.
- ALWAYS transfer to a pipeline after getting the script. Never return the script as your final answer.
- The pipeline will handle TTS, image generation, and video composition automatically.
""",
    tools=[generate_script],
    output_key="script_output",
    sub_agents=[general_pipeline, maths_pipeline],
)
