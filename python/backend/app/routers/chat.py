"""
Chat router — main entry point for all text conversations.

Flow: 4-tier intent cascade → LangGraph agent → response
Tier 1: follow-up (0ms) → Tier 2: keyword scoring (0ms) → Tier 3: embedding (~10ms) → Tier 4: LLM (1-2s)
"""
import uuid
import time
import logging
from typing import Any, Optional

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


# Field ask priority (single field per turn) — Part 4.3
_FIELD_PRIORITY_DEFAULT = [
    "monthly_income",
    "age",
    "monthly_expenses",
    "fire_target_age",
    "rent_paid",
    "city",
    "parents_health_premium",
    "parents_age_above_60",
    "nps_contribution",
]


def _next_missing_field(intent: str, missing: list[str]) -> str:
    if not missing:
        return ""
    tax_first = ["rent_paid", "city", "parents_health_premium", "parents_age_above_60", "nps_contribution"]
    if intent == "tax_wizard":
        order = _FIELD_PRIORITY_DEFAULT[:3] + tax_first + [
            m for m in missing if m not in set(_FIELD_PRIORITY_DEFAULT + tax_first)
        ]
    elif intent == "fire_planner":
        order = _FIELD_PRIORITY_DEFAULT[:3] + ["fire_target_age"] + [
            m for m in missing if m not in _FIELD_PRIORITY_DEFAULT
        ]
    elif intent == "couples_finance":
        order = _FIELD_PRIORITY_DEFAULT + ["partner_monthly_income"] + [
            m for m in missing if m not in set(_FIELD_PRIORITY_DEFAULT + ["partner_monthly_income"])
        ]
    else:
        order = _FIELD_PRIORITY_DEFAULT + [m for m in missing if m not in _FIELD_PRIORITY_DEFAULT]
    seen = set()
    for f in order:
        if f in missing and f not in seen:
            return f
    return missing[0]


def _merge_extraction(extracted: dict[str, Any]) -> dict[str, Any]:
    """Map extractor JSON → profile column overrides."""
    out: dict[str, Any] = {}
    if not extracted:
        return out
    if extracted.get("fire_target_age") is not None:
        out["fire_target_age"] = int(extracted["fire_target_age"])
    if extracted.get("amount") is not None:
        out["goal_target_amount"] = float(extracted["amount"])
    if extracted.get("years") is not None:
        out["goal_target_years"] = int(extracted["years"])
    if extracted.get("goal_type"):
        out["primary_goal"] = str(extracted["goal_type"])
    return out


@router.post("")
async def chat(
    body: ChatRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    session_id = body.session_id or str(uuid.uuid4())
    t0 = time.monotonic()

    last_intent = await get_last_intent(auth.user_id, session_id)
    intent_result = await classify_intent(body.message, last_intent=last_intent)
    intent = intent_result.intent
    logger.info(
        "Intent: %s (tier=%d/%s, conf=%.2f, %.1fms)",
        intent,
        intent_result.tier,
        intent_result.tier_name,
        intent_result.confidence,
        intent_result.latency_ms,
    )

    history = await get_conversation(auth.user_id, session_id, limit=10)

    from app.core.extractors import extract_financial_goal
    from app.core.llm import primary_llm

    extracted = await extract_financial_goal(body.message, primary_llm)
    profile_overrides = _merge_extraction(extracted)

    from app.agents.graph import run_agent

    result = await run_agent(
        user_id=auth.user_id,
        message=body.message,
        intent=intent,
        language=body.language,
        voice_mode=body.voice_mode,
        history=history,
        profile_overrides=profile_overrides,
    )

    ao = result.get("agent_outputs", {}).get(intent, {})
    if ao.get("status") == "PROFILE_INCOMPLETE":
        missing = ao.get("missing_fields") or []
        field = _next_missing_field(intent, missing)
        return {
            "type": "field_request",
            "field": field,
            "message": ao.get("message", ""),
            "allow_skip": True,
            "skip_label": "Use an estimate instead",
            "completeness_pct": ao.get("completeness_pct"),
            "intent": intent,
            "agent_used": intent,
            "session_id": session_id,
        }

    await save_message(auth.user_id, session_id, "user", body.message)
    await save_message(auth.user_id, session_id, "assistant", result["response"])
    await save_last_intent(auth.user_id, session_id, intent)

    from app.models import ConversationMessage

    db.add(
        ConversationMessage(
            user_id=auth.user_id,
            session_id=session_id,
            role="user",
            content=body.message,
            language=body.language,
            intent=intent,
            agent_used="",
        )
    )
    db.add(
        ConversationMessage(
            user_id=auth.user_id,
            session_id=session_id,
            role="assistant",
            content=result["response"],
            language=body.language,
            intent=intent,
            agent_used=result.get("agent_used", intent),
        )
    )
    await db.commit()

    try:
        from app.services.compliance import log_advice

        await log_advice(
            db=db,
            user_id=auth.user_id,
            session_id=session_id,
            intent=intent,
            agent_used=result.get("agent_used", intent),
            user_message=body.message,
            response_text=result["response"],
            agent_output=result.get("agent_outputs", {}),
            language=body.language,
            channel="web",
            response_time_ms=int((time.monotonic() - t0) * 1000),
        )
        await db.commit()
    except Exception:
        pass

    return {
        "type": "message",
        "response": result["response"],
        "intent": intent,
        "agent_used": result.get("agent_used", intent),
        "session_id": session_id,
        "agent_outputs": result.get("agent_outputs", {}),
    }


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
        from app.core.extractors import extract_financial_goal
        from app.core.llm import primary_llm
        from app.agents.graph import run_agent_stream

        extracted = await extract_financial_goal(body.message, primary_llm)
        profile_overrides = _merge_extraction(extracted)

        async for chunk in run_agent_stream(
            user_id=auth.user_id,
            message=body.message,
            intent=intent,
            language=body.language,
            voice_mode=body.voice_mode,
            history=history,
            profile_overrides=profile_overrides,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
