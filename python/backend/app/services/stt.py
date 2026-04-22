"""
STT service — faster-whisper (CPU) with Groq Whisper API fallback.
"""
import io
import logging
import tempfile
import os

from app.config import settings

logger = logging.getLogger("creda.stt")

_whisper_model = None


def _get_whisper_model():
    """Lazy-load faster-whisper model (CPU only)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",
        )
        logger.info("faster-whisper model '%s' loaded (CPU, int8)", settings.WHISPER_MODEL_SIZE)
    return _whisper_model


async def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Transcribe audio bytes → text.
    Chain: faster-whisper (CPU) → Groq Whisper API fallback.
    """
    # Try faster-whisper first
    try:
        return await _transcribe_faster_whisper(audio_bytes)
    except Exception as e:
        logger.warning("faster-whisper failed, falling back to Groq: %s", e)

    # Fallback: Groq Whisper API
    try:
        return await _transcribe_groq(audio_bytes)
    except Exception as e:
        logger.error("All STT engines failed: %s", e)
        return {"text": "", "language": "en", "confidence": 0}


async def _transcribe_faster_whisper(audio_bytes: bytes) -> dict:
    """Transcribe using faster-whisper (local CPU)."""
    import asyncio

    def _sync_transcribe():
        model = _get_whisper_model()
        # Write to temp file (faster-whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            segments, info = model.transcribe(tmp_path, beam_size=5)
            text = " ".join(seg.text for seg in segments).strip()
            return {
                "text": text,
                "language": info.language or "en",
                "confidence": round(info.language_probability or 0.9, 2),
            }
        finally:
            os.unlink(tmp_path)

    # Run in thread pool to avoid blocking the event loop
    return await asyncio.get_event_loop().run_in_executor(None, _sync_transcribe)


async def _transcribe_groq(audio_bytes: bytes) -> dict:
    """Fallback: Groq Whisper API."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            files={"file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")},
            data={"model": "whisper-large-v3", "response_format": "json"},
        )
        response.raise_for_status()
        data = response.json()
        return {
            "text": data.get("text", ""),
            "language": data.get("language", "en"),
            "confidence": 0.85,
        }
