"""
Chat router — main entry point for all text conversations.

Flow: 4-tier intent cascade → LangGraph agent → response
Tier 1: follow-up (0ms) → Tier 2: keyword scoring (0ms) → Tier 3: embedding (~10ms) → Tier 4: LLM (1-2s)
"""
import uuid
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.redis_client import save_message, get_conversation, save_last_intent, get_last_intent
from app.services.intent_engine import classify_intent

logger = logging.getLogger("creda.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "en"
    voice_mode: bool = False


class ChatResponse(BaseModel):
    response: str
    intent: str
    agent_used: str
    session_id: str


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    session_id = body.session_id or str(uuid.uuid4())
    t0 = time.monotonic()

    # Step 1: 4-tier intent classification cascade
    last_intent = await get_last_intent(auth.user_id, session_id)
    intent_result = await classify_intent(body.message, last_intent=last_intent)
    intent = intent_result.intent
    logger.info(
        "Intent: %s (tier=%d/%s, conf=%.2f, %.1fms)",
        intent, intent_result.tier, intent_result.tier_name,
        intent_result.confidence, intent_result.latency_ms,
    )

    # Step 2: get conversation history from Redis
    history = await get_conversation(auth.user_id, session_id, limit=10)

    # Step 3: build initial state and invoke LangGraph
    from app.agents.graph import run_agent
    result = await run_agent(
        user_id=auth.user_id,
        message=body.message,
        intent=intent,
        language=body.language,
        voice_mode=body.voice_mode,
        history=history,
    )

    # Step 4: persist to Redis (conversation history + intent for follow-up detection)
    await save_message(auth.user_id, session_id, "user", body.message)
    await save_message(auth.user_id, session_id, "assistant", result["response"])
    await save_last_intent(auth.user_id, session_id, intent)

    # Step 5: persist to PostgreSQL (permanent record)
    from app.models import ConversationMessage
    db.add(ConversationMessage(
        user_id=auth.user_id, session_id=session_id, role="user",
        content=body.message, language=body.language, intent=intent, agent_used="",
    ))
    db.add(ConversationMessage(
        user_id=auth.user_id, session_id=session_id, role="assistant",
        content=result["response"], language=body.language, intent=intent,
        agent_used=result.get("agent_used", intent),
    ))
    await db.commit()

    # Step 6: compliance — log advice for SEBI audit trail
    try:
        from app.services.compliance import log_advice
        await log_advice(
            db=db, user_id=auth.user_id, session_id=session_id,
            intent=intent, agent_used=result.get("agent_used", intent),
            user_message=body.message, response_text=result["response"],
            agent_output=result.get("agent_outputs", {}),
            language=body.language, channel="web",
            response_time_ms=int((time.monotonic() - t0) * 1000),
        )
        await db.commit()
    except Exception:
        pass  # compliance logging should never break chat

    return ChatResponse(
        response=result["response"],
        intent=intent,
        agent_used=result.get("agent_used", intent),
        session_id=session_id,
    )


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming endpoint for Django HTMX frontend."""
    session_id = body.session_id or str(uuid.uuid4())
    last_intent = await get_last_intent(auth.user_id, session_id)
    intent_result = await classify_intent(body.message, last_intent=last_intent)
    intent = intent_result.intent
    await save_last_intent(auth.user_id, session_id, intent)

    history = await get_conversation(auth.user_id, session_id, limit=10)

    async def event_generator():
        from app.agents.graph import run_agent_stream
        async for chunk in run_agent_stream(
            user_id=auth.user_id,
            message=body.message,
            intent=intent,
            language=body.language,
            voice_mode=body.voice_mode,
            history=history,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
