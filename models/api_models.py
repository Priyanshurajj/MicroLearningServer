from pydantic import BaseModel, Field
from typing import List


class GenerateRequest(BaseModel):
    transcript: str = Field(
        ...,
        description="The transcript or topic text to generate an educational reel from.",
        examples=[
            "Photosynthesis is the process by which plants convert sunlight into energy...",
            "The Pythagorean theorem states that a^2 + b^2 = c^2...",
        ],
    )


class AgentStepLog(BaseModel):
    agent_name: str = ""
    author: str = ""
    content_preview: str = ""
    is_final: bool = False


class PipelineResult(BaseModel):
    session_id: str = Field(..., description="Unique session ID for this generation")
    status: str = Field(..., description="Pipeline execution status")
    transcript_preview: str = Field(
        ..., description="Preview of the input transcript"
    )
    agent_response: str = Field(
        ..., description="Full response from the root agent"
    )
    agent_logs: List[AgentStepLog] = Field(
        default=[], description="Logs of each agent step in the pipeline"
    )
