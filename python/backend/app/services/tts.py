"""
TTS service — Kokoro → Edge TTS → Piper → gTTS fallback chain.
Target: <1.5s to first audio byte.
"""
import io
import logging

from app.config import settings

logger = logging.getLogger("creda.tts")

# Language → Edge TTS voice mapping (Indian languages + English)
_EDGE_VOICES = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "bn": "bn-IN-TanishaaNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "pa": "pa-IN-GurpreetNeural",
    "ur": "ur-IN-GulNeural",
}


async def synthesize_speech(text: str, language: str = "en", voice: str | None = None) -> bytes:
    """
    Synthesize text to audio bytes.
    Fallback chain: Kokoro (English) → Edge TTS (all languages) → Piper (English) → gTTS (all).
    For non-English, skip Kokoro and Piper (English-only engines).
    """
    is_english = language in ("en", "")

    # 1. Kokoro TTS (best quality, but English-only)
    if is_english:
        try:
            return await _kokoro_tts(text, language, voice)
        except Exception as e:
            logger.warning("Kokoro TTS failed: %s", e)

    # 2. Edge TTS (free, good quality, supports all 11 Indian languages)
    try:
        return await _edge_tts(text, language)
    except Exception as e:
        logger.warning("Edge TTS failed: %s", e)

    # 3. Piper TTS (local, English-only fallback)
    if is_english:
        try:
            return await _piper_tts(text)
        except Exception as e:
            logger.warning("Piper TTS failed: %s", e)

    # 4. gTTS (last resort, slow but supports all languages)
    return await _gtts_fallback(text, language)


async def _kokoro_tts(text: str, language: str, voice: str | None) -> bytes:
    """Kokoro TTS via Docker container (OpenAI-compatible API)."""
    import httpx

    # Kokoro voices — use English voices as primary since Kokoro
    # is strongest in English. For non-English text, Edge TTS or gTTS
    # will handle better via the fallback chain.
    _KOKORO_VOICES = {
        "en": "af_heart",
        "hi": "af_heart",
        "ta": "af_heart",
        "te": "af_heart",
        "bn": "af_heart",
        "mr": "af_heart",
        "gu": "af_heart",
        "kn": "af_heart",
        "ml": "af_heart",
        "pa": "af_heart",
        "ur": "af_heart",
    }

    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice or _KOKORO_VOICES.get(language, "af_heart"),
        "response_format": "wav",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.KOKORO_TTS_URL}/v1/audio/speech",
            json=payload,
        )
        resp.raise_for_status()
        return resp.content


async def _edge_tts(text: str, language: str) -> bytes:
    """Microsoft Edge TTS — free, high quality, supports Indian languages."""
    import edge_tts

    voice = _EDGE_VOICES.get(language, _EDGE_VOICES["en"])
    communicate = edge_tts.Communicate(text, voice)

    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])

    audio_bytes = audio_data.getvalue()
    if not audio_bytes:
        raise ValueError("Edge TTS returned empty audio")
    return audio_bytes


async def _piper_tts(text: str) -> bytes:
    """Piper TTS via Wyoming protocol (Docker container)."""
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.PIPER_TTS_URL}/api/tts",
            json={"text": text},
        )
        resp.raise_for_status()
        return resp.content


async def _gtts_fallback(text: str, language: str) -> bytes:
    """gTTS — last resort. Slow but works."""
    import asyncio
    from gtts import gTTS

    def _sync_gtts():
        lang_code = language[:2] if language else "en"
        tts = gTTS(text=text, lang=lang_code)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()

    return await asyncio.get_event_loop().run_in_executor(None, _sync_gtts)
