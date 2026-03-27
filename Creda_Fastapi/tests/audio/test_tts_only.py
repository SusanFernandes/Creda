"""
test_tts_only.py — Tests for /tts_only and /transcribe_only endpoints.

/tts_only: Text → Speech (no audio input needed)
/transcribe_only: Audio → Text (needs audio files)

Run: pytest tests/audio/test_tts_only.py -v
"""

import pytest
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────
# /transcribe_only — needs audio files
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcribe_only_english(multilingual_client, sample_en_wav: Path):
    """
    /transcribe_only with English audio should return transcription.
    """
    with open(sample_en_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/transcribe_only",
            files={"audio": ("sample_en.wav", f, "audio/wav")},
            data={"language_code": "en"},
        )

    assert resp.status_code == 200, f"Expected 200: {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "transcript" in data or "text" in data or "transcription" in data, (
        f"Response missing transcript field: {data}"
    )


@pytest.mark.asyncio
async def test_transcribe_only_silence(multilingual_client, silence_wav: Path):
    """
    /transcribe_only with silence should handle gracefully.
    """
    with open(silence_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/transcribe_only",
            files={"audio": ("silence.wav", f, "audio/wav")},
            data={"language_code": "en"},
        )

    # Should be 200 (empty/short transcript) or graceful error, never 500
    assert resp.status_code in (200, 400, 422), (
        f"Silence caused crash: {resp.status_code}: {resp.text}"
    )
