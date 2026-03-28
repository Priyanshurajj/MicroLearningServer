import asyncio
import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.agent import root_agent

logger = logging.getLogger("EduReelADK")

APP_NAME = "EduReelADK"
session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

async def run_agent_pipeline(
    user_id: str, session_id: str, transcript: str
) -> tuple[str, list[dict]]:
    try:
        return await _execute_pipeline(user_id, session_id, transcript)
    except Exception as e:
        raise


async def _execute_pipeline(
    user_id: str, session_id: str, transcript: str
) -> tuple[str, list[dict]]:
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=transcript)],
    )

    final_response_text = ""
    agent_logs = []

    logger.info(f"PIPELINE START | session={session_id}")

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        agent_name = getattr(event, "agent_name", "unknown")
        author = event.author if hasattr(event, "author") and event.author else "system"
        is_final = event.is_final_response()

        content_text = ""
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    content_text += part.text
                elif part.function_call:
                    content_text += (
                        f"[TOOL CALL: {part.function_call.name}"
                        f"({dict(part.function_call.args) if part.function_call.args else {}})]"
                    )
                elif part.function_response:
                    content_text += f"[TOOL RESPONSE: {part.function_response.name}]"

        status_tag = "FINAL" if is_final else ""
        preview = content_text + ("..." if len(content_text) > 200 else "")
        logger.info(f"Agent: {agent_name} | Author: {author}{status_tag}")
        logger.info(f"Content: {preview}")

        agent_logs.append({
            "agent_name": agent_name,
            "author": author,
            "content_preview": content_text[:500],
            "is_final": is_final,
        })

        if is_final and content_text:
            final_response_text += content_text

    logger.info(f"PIPELINE END | Total steps: {len(agent_logs)}")
    return final_response_text, agent_logs

