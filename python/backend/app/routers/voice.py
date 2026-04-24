"""
Voice router — STT transcription, TTS synthesis, combined voice pipeline,
and intent-based voice navigation (the global floating-mic hero feature).
"""
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.auth import AuthContext, get_auth

router = APIRouter()

# ── Intent → page URL mapping ──────────────────────────────────────
_INTENT_TO_PAGE = {
    "portfolio_xray": "/portfolio/",
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
):
    """
    Full voice pipeline: transcribe → chat → synthesize.
    Returns audio response directly.
    """
    from fastapi.responses import StreamingResponse
    import uuid

    # 1. Transcribe
    audio_bytes = await audio.read()
    from app.services.stt import transcribe_audio
    stt_result = await transcribe_audio(audio_bytes)
    detected_lang = stt_result["language"]

    # 2. Chat (reuse the chat logic with voice_mode=True)
    from app.agents.graph import run_agent
    from app.services.intent_engine import classify_intent
    from app.redis_client import save_message, get_conversation, save_last_intent, get_last_intent

    sid = session_id or str(uuid.uuid4())
    message = stt_result["text"]
    last_intent = await get_last_intent(auth.user_id, sid)
    intent_result = await classify_intent(message, last_intent=last_intent)
    intent = intent_result.intent

    history = await get_conversation(auth.user_id, sid, limit=10)
    result = await run_agent(
        user_id=auth.user_id,
        message=message,
        intent=intent,
        language=detected_lang,
        voice_mode=True,
        history=history,
    )

    await save_message(auth.user_id, sid, "user", message)
    await save_message(auth.user_id, sid, "assistant", result["response"])
    await save_last_intent(auth.user_id, sid, intent)

    # 3. Synthesize response
    from app.services.tts import synthesize_speech
    response_audio = await synthesize_speech(result["response"], detected_lang)

    return StreamingResponse(
        io.BytesIO(response_audio),
        media_type="audio/wav",
        headers={
            "X-Transcript": stt_result["text"],
            "X-Response-Text": result["response"],
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
):
    """
    Voice Navigation — the hero floating-mic endpoint.
    Transcribes → classifies intent → determines page → synthesizes brief redirect speech.
    Returns JSON with { transcript, intent, page_url, page_label, response_text, audio_b64 }.
    The full agent answer is deferred — the frontend navigates to the page first.
    """
    import base64
    import uuid

    # 1. Transcribe
    audio_bytes = await audio.read()
    from app.services.stt import transcribe_audio
    stt_result = await transcribe_audio(audio_bytes)
    detected_lang = stt_result["language"]
    message = stt_result["text"]

    # 2. Classify intent
    from app.services.intent_engine import classify_intent
    from app.redis_client import get_last_intent, save_last_intent

    sid = session_id or str(uuid.uuid4())
    last_intent = await get_last_intent(auth.user_id, sid)
    intent_result = await classify_intent(message, last_intent=last_intent)
    intent = intent_result.intent
    await save_last_intent(auth.user_id, sid, intent)

    # 3. Map intent to page
    page_url = _INTENT_TO_PAGE.get(intent, "/chat/")
    page_label = _INTENT_LABELS.get(intent, "AI Chat")

    # 4. Generate a brief spoken redirect acknowledgement
    if detected_lang.startswith("hi"):
        ack_text = f"ज़रूर, मैं आपको {page_label} पर ले जाता हूँ।"
    elif detected_lang.startswith("ta"):
        ack_text = f"நிச்சயமாக, {page_label} பக்கத்திற்கு செல்கிறேன்."
    elif detected_lang.startswith("te"):
        ack_text = f"తప్పకుండా, {page_label} పేజీకి తీసుకువెళ్తున్నాను."
    elif detected_lang.startswith("bn"):
        ack_text = f"অবশ্যই, আপনাকে {page_label} পেজে নিয়ে যাচ্ছি।"
    else:
        ack_text = f"Sure, taking you to {page_label}."

    # 5. Synthesize the brief acknowledgement audio
    from app.services.tts import synthesize_speech
    try:
        audio_response = await synthesize_speech(ack_text, detected_lang)
        audio_b64 = base64.b64encode(audio_response).decode("ascii")
    except Exception:
        audio_b64 = ""

    return {
        "transcript": message,
        "intent": intent,
        "page_url": page_url,
        "page_label": page_label,
        "response_text": ack_text,
        "audio_b64": audio_b64,
        "language": detected_lang,
    }
