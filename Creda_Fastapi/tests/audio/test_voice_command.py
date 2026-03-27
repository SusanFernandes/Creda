"""
test_voice_command.py — Tests for /voice/command push-to-talk endpoint.

These tests require audio files. Place them in tests/audio/:
  - sample_en.wav  (short English speech, e.g. "show my portfolio")
  - sample_hi.wav  (short Hindi speech)
  - silence.wav    (2 seconds of silence)

Run: pytest tests/audio/test_voice_command.py -v
Skip if no audio: pytest tests/audio/ -v  (auto-skips missing files)
"""

import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_voice_command_english(multilingual_client, sample_en_wav: Path):
    """
    /voice/command with English audio should return structured JSON:
    {transcript, type, response, ...}
    """
    with open(sample_en_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/voice/command",
            files={"audio": ("sample_en.wav", f, "audio/wav")},
            data={
                "language_code": "en",
                "current_screen": "dashboard",
                "user_id": "test_user",
            },
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "transcript" in data, f"Response missing 'transcript': {data}"
    assert "type" in data, f"Response missing 'type': {data}"


@pytest.mark.asyncio
async def test_voice_command_hindi(multilingual_client, sample_hi_wav: Path):
    """
    /voice/command with Hindi audio should work with language_code=hi.
    """
    with open(sample_hi_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/voice/command",
            files={"audio": ("sample_hi.wav", f, "audio/wav")},
            data={
                "language_code": "hi",
                "current_screen": "dashboard",
                "user_id": "test_user",
            },
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "transcript" in data


@pytest.mark.asyncio
async def test_voice_command_silence(multilingual_client, silence_wav: Path):
    """
    /voice/command with silence should not crash — should return empty or
    low-confidence transcription.
    """
    with open(silence_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/voice/command",
            files={"audio": ("silence.wav", f, "audio/wav")},
            data={
                "language_code": "en",
                "current_screen": "dashboard",
                "user_id": "test_user",
            },
        )

    # Should not crash — either 200 with empty transcript or a graceful error
    assert resp.status_code in (200, 400, 422), (
        f"Silence caused unexpected error: {resp.status_code} {resp.text}"
    )


@pytest.mark.asyncio
async def test_voice_command_default_params(multilingual_client, sample_en_wav: Path):
    """
    /voice/command with only audio file (default params) should work.
    language_code defaults to "en", current_screen to "dashboard".
    """
    with open(sample_en_wav, "rb") as f:
        resp = await multilingual_client.post(
            "/voice/command",
            files={"audio": ("sample_en.wav", f, "audio/wav")},
        )

    assert resp.status_code in (200, 422), f"Unexpected: {resp.status_code}: {resp.text}"
