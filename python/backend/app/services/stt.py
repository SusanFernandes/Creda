"""
STT service — faster-whisper (CPU) with Groq Whisper API fallback.
"""
# `audioop` is stdlib on 3.12-; 3.13+ needs the `audioop-lts` package (see requirements.txt) for pydub.
try:
    import audioop  # noqa: F401
except ImportError:
    pass
import io
import logging
import tempfile
import os

from app.config import settings

logger = logging.getLogger("creda.stt")

_whisper_model = None


def _get_whisper_model():
    """Lazy-load faster-whisper model (CPU only). Prefers local model path."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        from pathlib import Path
        # Check for locally downloaded model first
        local_path = Path(__file__).resolve().parents[3] / "models" / f"faster-whisper-{settings.WHISPER_MODEL_SIZE}"
        model_id = str(local_path) if local_path.exists() else settings.WHISPER_MODEL_SIZE
        _whisper_model = WhisperModel(
            model_id,
            device="cpu",
            compute_type="int8",
        )
        logger.info("faster-whisper model loaded from '%s' (CPU, int8)", model_id)
    return _whisper_model


def _convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert any audio format (WebM, OGG, MP3, etc.) to WAV using pydub.
    Returns original bytes if ffmpeg is not available."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        return wav_buffer.getvalue()
    except Exception as e:
        logger.warning("Audio conversion failed (ffmpeg may be missing), using raw bytes: %s", e)
        return audio_bytes


def _detect_audio_format(audio_bytes: bytes) -> str:
    """Detect audio format from magic bytes."""
    if audio_bytes[:4] == b"RIFF":
        return "wav"
    if audio_bytes[:4] == b"OggS":
        return "ogg"
    if audio_bytes[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
        return "mp3"
    return "webm"  # default for browser MediaRecorder


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
        # Try WAV conversion first; if ffmpeg missing, write raw bytes with correct extension
        wav_bytes = _convert_to_wav(audio_bytes)
        ext = ".wav" if wav_bytes[:4] == b"RIFF" else f".{_detect_audio_format(audio_bytes)}"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(wav_bytes)
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
    """Fallback: Groq Whisper API (retries on 429 to align with chat rate limits)."""
    import asyncio
    import httpx

    # Try WAV conversion; if fails, send raw with detected mime type
    wav_bytes = _convert_to_wav(audio_bytes)
    if wav_bytes[:4] == b"RIFF":
        fname, mime = "audio.wav", "audio/wav"
    else:
        fmt = _detect_audio_format(audio_bytes)
        fname = f"audio.{fmt}"
        mime = f"audio/{fmt}"

    delays = (0.0, 2.0, 6.0)
    last_exc: BaseException | None = None
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt, delay in enumerate(delays):
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    files={"file": (fname, io.BytesIO(wav_bytes), mime)},
                    data={"model": "whisper-large-v3", "response_format": "json"},
                )
                if response.status_code == 429 and attempt < len(delays) - 1:
                    last_exc = RuntimeError("Groq STT 429")
                    continue
                response.raise_for_status()
                data = response.json()
                return {
                    "text": data.get("text", ""),
                    "language": data.get("language", "en"),
                    "confidence": 0.85,
                }
            except httpx.HTTPStatusError as e:
                last_exc = e
                if e.response is not None and e.response.status_code == 429 and attempt < len(delays) - 1:
                    continue
                raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Groq transcription: empty retry path")
