"""
WhatsApp router — Twilio webhook + account linking.

Linked users: messages run with real user_id and DB profile.
Unlinked: reply with one-time link code to bind phone to CREDA account.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.config import settings
from app.database import get_db
from app.models import UserProfile, WhatsAppSession

logger = logging.getLogger("creda.whatsapp")

router = APIRouter()

_LINK_CODE_TTL_HOURS = 48


class WhatsappLinkBody(BaseModel):
    code: str


def _escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def _resolve_user_id_for_phone(phone: str, db: AsyncSession) -> str | None:
    r = await db.execute(select(UserProfile).where(UserProfile.whatsapp_phone == phone))
    prof = r.scalar_one_or_none()
    if prof:
        return prof.user_id
    r2 = await db.execute(select(WhatsAppSession).where(WhatsAppSession.phone_number == phone))
    sess = r2.scalar_one_or_none()
    if sess and sess.user_id:
        return sess.user_id
    return None


@router.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(""),
    From: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    phone = From.replace("whatsapp:", "").strip()
    message = (Body or "").strip()

    if not phone:
        return Response(content="<Response></Response>", media_type="application/xml")

    user_id = await _resolve_user_id_for_phone(phone, db)

    if not user_id:
        r = await db.execute(select(WhatsAppSession).where(WhatsAppSession.phone_number == phone))
        session = r.scalar_one_or_none()
        if not session:
            session = WhatsAppSession(phone_number=phone, language="hi")
            db.add(session)
            await db.flush()
        code = secrets.token_urlsafe(16)[:32]
        session.link_code = code
        session.link_code_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=_LINK_CODE_TTL_HOURS
        )
        await db.commit()
        base = (settings.PUBLIC_APP_URL or "https://creda.in").rstrip("/")
        link = f"{base}/whatsapp/link?code={code}"
        reply = (
            "Hi! Link this number to your CREDA account for personalised advice.\n"
            f"Open: {link}\n"
            f"(Code expires in {_LINK_CODE_TTL_HOURS}h.)"
        )
        return Response(
            content=f"<Response><Message>{_escape_xml(reply)}</Message></Response>",
            media_type="application/xml",
        )

    from app.services.intent_engine import classify_intent
    from app.redis_client import get_conversation, get_last_intent, save_last_intent, save_message

    last_intent = await get_last_intent(user_id, "whatsapp")
    intent_result = await classify_intent(message, last_intent=last_intent)
    intent = intent_result.intent
    history = await get_conversation(user_id, "whatsapp", limit=10)

    from app.agents.graph import run_agent

    chat_result = await run_agent(
        user_id=user_id,
        message=message,
        intent=intent,
        language="hi",
        voice_mode=False,
        history=history,
    )

    await save_message(user_id, "whatsapp", "user", message)
    await save_message(user_id, "whatsapp", "assistant", chat_result["response"])
    await save_last_intent(user_id, "whatsapp", intent)

    r = await db.execute(select(WhatsAppSession).where(WhatsAppSession.phone_number == phone))
    session = r.scalar_one_or_none()
    if session:
        session.last_message_at = datetime.utcnow()
        await db.commit()

    reply = chat_result["response"]
    return Response(
        content=f"<Response><Message>{_escape_xml(reply)}</Message></Response>",
        media_type="application/xml",
    )


@router.post("/link")
async def complete_whatsapp_link_post(
    body: WhatsappLinkBody,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Bind WhatsApp session `code` to the logged-in user's profile."""
    code = body.code.strip()
    if not code or len(code) < 8:
        raise HTTPException(400, "Invalid code")
    r = await db.execute(select(WhatsAppSession).where(WhatsAppSession.link_code == code))
    session = r.scalar_one_or_none()
    if not session or not session.link_code_expires_at:
        raise HTTPException(404, "Link code not found")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if session.link_code_expires_at < now:
        raise HTTPException(410, "Link code expired")

    phone = session.phone_number
    prof_r = await db.execute(select(UserProfile).where(UserProfile.user_id == auth.user_id))
    profile = prof_r.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    profile.whatsapp_phone = phone
    session.user_id = auth.user_id
    session.link_code = None
    session.link_code_expires_at = None
    session.is_verified = True
    await db.commit()
    return {"status": "ok", "whatsapp_phone": phone}
