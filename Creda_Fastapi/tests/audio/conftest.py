"""
conftest.py — Shared fixtures for audio tests.

Audio tests require:
  - Backend services running (or use TestClient)
  - Audio files in this directory (see __init__.py for required files)
  - Models loaded (ASR, TTS — so these are slow tests)
"""

import os
import sys
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Ensure Creda_Fastapi is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

AUDIO_DIR = Path(__file__).parent


def _audio_file(name: str) -> Path:
    """Resolve an audio file path, raising skip if missing."""
    p = AUDIO_DIR / name
    if not p.exists():
        pytest.skip(f"Audio file not found: {p}. Place it in tests/audio/")
    return p


@pytest.fixture
def sample_en_wav() -> Path:
    return _audio_file("sample_en.wav")


@pytest.fixture
def sample_hi_wav() -> Path:
    return _audio_file("sample_hi.wav")


@pytest.fixture
def silence_wav() -> Path:
    return _audio_file("silence.wav")


@pytest.fixture
async def multilingual_client():
    """
    Async test client for multilingual service.
    WARNING: This triggers model loading (30-60s on first use).
    """
    from fastapi1_multilingual import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
