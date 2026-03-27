"""
test_pipecat_import.py — Verify pipecat_bot.py import guard works correctly.

BUG (multilingual_py.log):
  pipecat_bot.py import guard logged:
    "pipecat-ai[webrtc,silero] not installed — real-time voice disabled"
  
  This is correct behavior when extras aren't installed, BUT:
  - The import guard must set PIPECAT_AVAILABLE correctly
  - After installing extras, PIPECAT_AVAILABLE must become True
  - Service functions must be importable either way (stub or real)

These tests verify the import system works both ways.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_pipecat_bot_importable():
    """pipecat_bot.py must be importable without crashing, regardless of extras."""
    import pipecat_bot
    assert hasattr(pipecat_bot, "PIPECAT_AVAILABLE")
    assert hasattr(pipecat_bot, "run_pipecat_bot")
    assert hasattr(pipecat_bot, "create_connection_from_offer")


def test_pipecat_available_is_bool():
    """PIPECAT_AVAILABLE must be a boolean."""
    from pipecat_bot import PIPECAT_AVAILABLE
    assert isinstance(PIPECAT_AVAILABLE, bool)


def test_pipecat_available_matches_extras():
    """
    PIPECAT_AVAILABLE should be True iff the webrtc extras are installed.
    After `uv pip install "pipecat-ai[webrtc,silero]"`, it should be True.
    """
    from pipecat_bot import PIPECAT_AVAILABLE

    try:
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
        extras_installed = True
    except ImportError:
        extras_installed = False

    assert PIPECAT_AVAILABLE == extras_installed, (
        f"PIPECAT_AVAILABLE={PIPECAT_AVAILABLE} but extras_installed={extras_installed}"
    )


def test_run_pipecat_bot_is_callable():
    """run_pipecat_bot must be a callable (real function or stub)."""
    from pipecat_bot import run_pipecat_bot
    assert callable(run_pipecat_bot)


def test_create_connection_is_callable():
    """create_connection_from_offer must be a callable."""
    from pipecat_bot import create_connection_from_offer
    assert callable(create_connection_from_offer)


def test_stub_raises_when_unavailable():
    """
    When PIPECAT_AVAILABLE is False, run_pipecat_bot (the stub) should
    raise RuntimeError. When True, it's the real function.
    """
    from pipecat_bot import PIPECAT_AVAILABLE, run_pipecat_bot
    import asyncio

    if not PIPECAT_AVAILABLE:
        with pytest.raises(RuntimeError, match="not installed"):
            asyncio.get_event_loop().run_until_complete(
                run_pipecat_bot(None)
            )
    # If available, we can't easily test without a real WebRTC connection,
    # so we just verify it's importable (already done above).


def test_sessions_dict_exists():
    """_sessions dict must exist for tracking active connections."""
    from pipecat_bot import _sessions
    assert isinstance(_sessions, dict)
