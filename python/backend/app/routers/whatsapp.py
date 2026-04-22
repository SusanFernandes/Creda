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

    # Route through 4-tier intent cascade
    from app.services.intent_engine import classify_intent
    from app.redis_client import save_message, get_conversation, save_last_intent, get_last_intent

    wa_id = f"wa:{phone}"
    last_intent = await get_last_intent(wa_id, "whatsapp")
    intent_result = await classify_intent(message, last_intent=last_intent)
    intent = intent_result.intent

    history = await get_conversation(wa_id, "whatsapp", limit=10)

    from app.agents.graph import run_agent
    chat_result = await run_agent(
        user_id=session.user_id or wa_id,
        message=message,
        intent=intent,
        language=session.language,
        voice_mode=False,
        history=history,
        db=db,
    )

    await save_message(wa_id, "whatsapp", "user", message)
    await save_message(wa_id, "whatsapp", "assistant", chat_result["response"])
    await save_last_intent(wa_id, "whatsapp", intent)

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
