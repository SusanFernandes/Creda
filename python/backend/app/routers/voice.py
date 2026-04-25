"""
Voice router — STT transcription, TTS synthesis, combined voice pipeline,
and intent-based voice navigation (the global floating-mic hero feature).
"""
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db

router = APIRouter()

# ── Intent → page URL mapping ──────────────────────────────────────
_INTENT_TO_PAGE = {
    "dashboard": "/dashboard/",
    "portfolio": "/portfolio/",
    "portfolio_xray": "/portfolio/xray/",
    "stress_test": "/stress-test/",
    "fire_planner": "/fire/",
    "money_health": "/health/",
    "tax_wizard": "/tax/",
    "tax_copilot": "/tax/",
    "budget_coach": "/budget/",
    "expense_analytics": "/expenses/",
    "goal_planner": "/goals/",
    "goal_simulator": "/goals/",
    "couples_finance": "/couples/",
    "sip_calculator": "/sip-calculator/",
    "market_pulse": "/market-pulse/",
    "money_personality": "/personality/",
    "social_proof": "/social-proof/",
    "et_research": "/research/",
    "rag_query": "/research/",
    "human_handoff": "/advisor/",
    "family_wealth": "/family/",
    "general_chat": "/chat/",
}

_INTENT_LABELS = {
    "dashboard": "Dashboard",
    "portfolio": "Portfolio",
    "portfolio_xray": "Portfolio X-Ray",
    "stress_test": "Stress Test",
    "fire_planner": "FIRE Planner",
    "money_health": "Money Health",
    "tax_wizard": "Tax Wizard",
    "tax_copilot": "Tax Wizard",
    "budget_coach": "Budget Coach",
    "expense_analytics": "Expense Analytics",
    "goal_planner": "Goals",
    "goal_simulator": "Goals",
    "couples_finance": "Couples Finance",
    "sip_calculator": "SIP Calculator",
    "market_pulse": "Market Pulse",
    "money_personality": "Money Personality",
    "social_proof": "Peer Insights",
    "et_research": "Research",
    "rag_query": "Research",
    "human_handoff": "Advisor",
    "family_wealth": "Family Wealth",
    "general_chat": "AI Chat",
}


class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth),
):
    """Transcribe audio using faster-whisper (CPU) → Groq Whisper fallback."""
    audio_bytes = await audio.read()
    from app.services.stt import transcribe_audio
    result = await transcribe_audio(audio_bytes)
    return TranscriptionResponse(
        text=result["text"],
        language=result["language"],
        confidence=result.get("confidence", 0.9),
    )


@router.post("/speak")
async def speak(
    body: TTSRequest,
    auth: AuthContext = Depends(get_auth),
):
    """Synthesize speech: Kokoro → Edge TTS → Piper → gTTS fallback chain."""
    from fastapi.responses import StreamingResponse
    from app.services.tts import synthesize_speech
    audio_bytes = await synthesize_speech(body.text, body.language, body.voice)
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=speech.wav"},
    )


@router.post("/pipeline")
async def voice_pipeline(
    audio: UploadFile = File(...),
    session_id: Optional[str] = None,
    language: str = "en",
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Full voice pipeline: transcribe → Groq command parse (intent + optional expenses) →
    persist expenses → chat (skipped for pure log-only commands) → synthesize.
    Returns audio response directly.
    """
    from fastapi.responses import StreamingResponse

    from app.agents.graph import run_agent
    from app.redis_client import get_conversation, get_last_intent, save_last_intent, save_message
    from app.services.expense_voice import apply_voice_expenses
    from app.services.intent_engine import classify_intent
    from app.services.stt import transcribe_audio_voice
    from app.services.tts import synthesize_speech
    from app.services.voice_command_parser import parse_voice_command
    from app.services.voice_nav_intent import resolve_voice_page_intent

    audio_bytes = await audio.read()
    stt_result = await transcribe_audio_voice(audio_bytes)
    detected_lang = stt_result["language"]
    message = stt_result["text"]

    sid = session_id or str(uuid.uuid4())
    last_intent = await get_last_intent(auth.user_id, sid)

    parsed = await parse_voice_command(message, last_intent=last_intent)
    expense_ids: list[str] = []
    if parsed and parsed.expenses:
        expense_ids = await apply_voice_expenses(db, auth.user_id, parsed.expenses)

    if parsed and parsed.skip_agent and expense_ids:
        intent = "expense_analytics"
        n = len(expense_ids)
        result_text = (
            f"I've logged {n} expense{'s' if n > 1 else ''} for you. "
            "Open Expenses anytime to review categories and totals."
        )
    else:
        if parsed:
            raw_intent = parsed.intent
            agent_message = parsed.normalized_message or message
        else:
            intent_result = await classify_intent(message, last_intent=last_intent, fast=True)
            raw_intent = intent_result.intent
            agent_message = message

        intent = resolve_voice_page_intent(
            message, raw_intent, has_logged_expenses=bool(expense_ids),
        )

        history = await get_conversation(auth.user_id, sid, limit=10)
        result = await run_agent(
            user_id=auth.user_id,
            message=agent_message,
            intent=intent,
            language=detected_lang,
            voice_mode=True,
            history=history,
        )
        result_text = result["response"]

    await save_message(auth.user_id, sid, "user", message)
    await save_message(auth.user_id, sid, "assistant", result_text)
    await save_last_intent(auth.user_id, sid, intent)

    response_audio = await synthesize_speech(result_text, detected_lang)

    return StreamingResponse(
        io.BytesIO(response_audio),
        media_type="audio/wav",
        headers={
            "X-Transcript": message,
            "X-Response-Text": result_text,
            "X-Intent": intent,
            "X-Language": detected_lang,
        },
    )


@router.post("/navigate")
async def voice_navigate(
    audio: UploadFile = File(...),
    session_id: Optional[str] = None,
    language: str = "en",
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Voice Navigation — floating mic: transcribe → Groq JSON (intent + expenses) →
    persist expenses → page URL + brief TTS. Falls back to fast keyword/LLM intent if parse fails.
    """
    import base64

    from app.redis_client import get_last_intent, save_last_intent
    from app.services.expense_voice import apply_voice_expenses
    from app.services.intent_engine import classify_intent
    from app.services.stt import transcribe_audio_voice
    from app.services.tts import synthesize_speech
    from app.services.voice_command_parser import parse_voice_command
    from app.services.voice_nav_intent import resolve_voice_page_intent

    audio_bytes = await audio.read()
    stt_result = await transcribe_audio_voice(audio_bytes)
    detected_lang = stt_result["language"]
    message = stt_result["text"]

    sid = session_id or str(uuid.uuid4())
    last_intent = await get_last_intent(auth.user_id, sid)

    parsed = await parse_voice_command(message, last_intent=last_intent)
    expense_ids: list[str] = []
    if parsed and parsed.expenses:
        expense_ids = await apply_voice_expenses(db, auth.user_id, parsed.expenses)

    if parsed:
        raw_intent = "expense_analytics" if expense_ids else parsed.intent
    else:
        intent_result = await classify_intent(message, last_intent=last_intent, fast=True)
        raw_intent = intent_result.intent

    intent = resolve_voice_page_intent(
        message, raw_intent, has_logged_expenses=bool(expense_ids),
    )

    await save_last_intent(auth.user_id, sid, intent)

    page_url = _INTENT_TO_PAGE.get(intent, "/chat/")
    page_label = _INTENT_LABELS.get(intent, "AI Chat")

    from app.services.voice_nav_brief import generate_nav_voice_brief, wants_personalized_nav_brief

    expense_note = ""
    if expense_ids:
        expense_note = (
            f"On this same request the user logged {len(expense_ids)} expense(s); acknowledge briefly if natural."
        )

    rich_ack: str | None = None
    if wants_personalized_nav_brief(message) or (parsed and getattr(parsed, "speak_brief", False)):
        rich_ack = await generate_nav_voice_brief(
            db,
            auth.user_id,
            intent,
            page_label,
            message,
            detected_lang,
            expense_note=expense_note,
        )

    if rich_ack:
        base_ack = rich_ack
    elif detected_lang.startswith("hi"):
        base_ack = f"ज़रूर, मैं आपको {page_label} पर ले जाता हूँ।"
    elif detected_lang.startswith("ta"):
        base_ack = f"நிச்சயமாக, {page_label} பக்கத்திற்கு செல்கிறேன்."
    elif detected_lang.startswith("te"):
        base_ack = f"తప్పకుండా, {page_label} పేజీకి తీసుకువెళ్తున్నాను."
    elif detected_lang.startswith("bn"):
        base_ack = f"অবশ্যই, আপনাকে {page_label} পেজে নিয়ে যাচ্ছি।"
    else:
        base_ack = f"Sure, taking you to {page_label}."
        if expense_ids:
            base_ack = (
                f"I've logged {len(expense_ids)} expense{'s' if len(expense_ids) > 1 else ''}. {base_ack}"
            )

    try:
        audio_response = await synthesize_speech(base_ack, detected_lang)
        audio_b64 = base64.b64encode(audio_response).decode("ascii")
    except Exception:
        audio_b64 = ""

    return {
        "transcript": message,
        "normalized_message": (parsed.normalized_message if parsed else message),
        "intent": intent,
        "page_url": page_url,
        "page_label": page_label,
        "response_text": base_ack,
        "audio_b64": audio_b64,
        "language": detected_lang,
        "expenses_logged": len(expense_ids),
        "expense_ids": expense_ids,
    }
