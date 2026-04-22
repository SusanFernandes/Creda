"""
Voice router — STT transcription, TTS synthesis, and combined voice pipeline.
"""
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.auth import AuthContext, get_auth

router = APIRouter()


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
