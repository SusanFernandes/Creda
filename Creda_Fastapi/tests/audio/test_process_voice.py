"""
test_process_voice.py — Tests for /process_voice endpoint.

These tests require audio files. Place them in tests/audio/:
  - sample_en.wav  (short English speech)
  - sample_hi.wav  (short Hindi speech)

Run: pytest tests/audio/test_process_voice.py -v
"""

import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_process_voice_english(multilingual_client, sample_en_wav: Path):
    """
    /process_voice processes audio and returns response text + audio.
    """
    with open(sample_en_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/process_voice",
            files={"audio": ("sample_en.wav", f, "audio/wav")},
            data={"language": "english"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_process_voice_hindi(multilingual_client, sample_hi_wav: Path):
    """
    /process_voice with Hindi audio.
    """
    with open(sample_hi_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/process_voice",
            files={"audio": ("sample_hi.wav", f, "audio/wav")},
            data={"language": "hindi"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_process_voice_no_language(multilingual_client, sample_en_wav: Path):
    """
    /process_voice without language parameter should use default (hindi).
    """
    with open(sample_en_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/process_voice",
            files={"audio": ("sample_en.wav", f, "audio/wav")},
        )

    # Should work or return a meaningful error, never 500
    assert resp.status_code in (200, 400, 422), (
        f"Unexpected error without language param: {resp.status_code}: {resp.text}"
    )
