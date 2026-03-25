import uuid
from fastapi import APIRouter, HTTPException

from models import GenerateRequest, AgentStepLog, PipelineResult
from services import run_agent_pipeline

router = APIRouter()

@router.post("/generate", response_model=PipelineResult, tags=["Pipeline"])
async def generate_reel(request: GenerateRequest):
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{uuid.uuid4().hex[:12]}"

    try:
        agent_response, agent_logs = await run_agent_pipeline(
            user_id=user_id,
            session_id=session_id,
            transcript=request.transcript,
        )

        return PipelineResult(
            session_id=session_id,
            status="completed",
            transcript_preview=request.transcript[:200] + (
                "..." if len(request.transcript) > 200 else ""
            ),
            agent_response=agent_response,
            agent_logs=[AgentStepLog(**log) for log in agent_logs],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}",
        )
