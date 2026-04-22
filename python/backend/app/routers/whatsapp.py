"""
WhatsApp router — Twilio webhook for incoming messages.
"""
import logging

from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import WhatsAppSession

logger = logging.getLogger("creda.whatsapp")

router = APIRouter()


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(""),
    From: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming WhatsApp messages via Twilio."""
    phone = From.replace("whatsapp:", "").strip()
    message = Body.strip()

    if not phone or not message:
        return Response(content="<Response></Response>", media_type="application/xml")

    # Find or create WhatsApp session
    result = await db.execute(
        select(WhatsAppSession).where(WhatsAppSession.phone_number == phone)
    )
    session = result.scalar_one_or_none()
    if not session:
        session = WhatsAppSession(phone_number=phone, language="hi")
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Route through chat pipeline
    from app.services.intent_classifier import keyword_pre_classify
    intent = keyword_pre_classify(message)
    if intent is None:
        from app.agents.intent_router import llm_classify_intent
        intent = await llm_classify_intent(message)

    from app.redis_client import save_message, get_conversation
    history = await get_conversation(f"wa:{phone}", "whatsapp", limit=10)

    from app.agents.graph import run_agent
    chat_result = await run_agent(
        user_id=session.user_id or f"wa:{phone}",
        message=message,
        intent=intent,
        language=session.language,
        voice_mode=False,
        history=history,
        db=db,
    )

    await save_message(f"wa:{phone}", "whatsapp", "user", message)
    await save_message(f"wa:{phone}", "whatsapp", "assistant", chat_result["response"])

    # Update last_message_at
    from datetime import datetime
    session.last_message_at = datetime.utcnow()
    await db.commit()

    # Reply via Twilio TwiML
    reply = chat_result["response"]
    twiml = f"<Response><Message>{_escape_xml(reply)}</Message></Response>"
    return Response(content=twiml, media_type="application/xml")


def _escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
