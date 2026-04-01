from google.adk.agents import Agent

from .config import TEXT_MODEL

storytelling_agent = Agent(
    name="storytelling_agent",
    model=TEXT_MODEL,
    description=(
        "Rewrites the raw educational transcript into a compelling narrative, "
        "preserving all facts while adding storytelling structure and engagement hooks."
    ),
    instruction=(
        "You are a master educational storyteller. "
        "Rewrite the user's transcript into an engaging narrative that: "
        "1) Grabs attention with relatable context or a surprising angle, "
        "2) Preserves ALL factual content and technical accuracy, "
        "3) Uses conversational, energetic language suitable for a young audience, "
        "4) Flows naturally from one idea to the next. "
        "Return ONLY the rewritten transcript text — no commentary, no headers, no markdown."
    ),
    output_key="narrative_transcript",
)
