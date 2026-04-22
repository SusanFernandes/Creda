"""
Chat router — main entry point for all text conversations.

Flow: keyword_pre_classify (~0ms) → LLM intent if needed → LangGraph agent → response
The keyword pre-classifier is a ROUTER-LEVEL gate, not a LangGraph node.
"""
import uuid
import time
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.redis_client import save_message, get_conversation
from app.services.intent_classifier import keyword_pre_classify

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

    # Step 1: keyword pre-classifier (~0ms, no LLM)
    intent = keyword_pre_classify(body.message)

    # Step 2: LLM intent classifier only if keywords didn't match
    if intent is None:
        from app.agents.intent_router import llm_classify_intent
        intent = await llm_classify_intent(body.message)

    # Step 3: get conversation history from Redis
    history = await get_conversation(auth.user_id, session_id, limit=10)

    # Step 4: build initial state and invoke LangGraph
    from app.agents.graph import run_agent
    result = await run_agent(
        user_id=auth.user_id,
        message=body.message,
        intent=intent,
        language=body.language,
        voice_mode=body.voice_mode,
        history=history,
    )

    # Step 5: persist to Redis (conversation history)
    await save_message(auth.user_id, session_id, "user", body.message)
    await save_message(auth.user_id, session_id, "assistant", result["response"])

    # Step 6: persist to PostgreSQL (permanent record)
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

    # Step 7: compliance — log advice for SEBI audit trail
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
    intent = keyword_pre_classify(body.message)
    if intent is None:
        from app.agents.intent_router import llm_classify_intent
        intent = await llm_classify_intent(body.message)

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
            db=db,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
