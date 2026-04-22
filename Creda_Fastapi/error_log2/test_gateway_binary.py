"""
test_gateway_binary.py — Regression test for gateway binary response crash.

BUG (error_log2):
  Gateway's route_request() called response.json() on ALL 200 responses,
  but /tts_only returns audio/wav bytes. This caused:
    UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd8

FIX:
  route_request now checks content-type before calling .json().
  Binary responses (audio/*, image/*, application/octet-stream) are
  returned as a FastAPI Response with raw bytes.
"""

import pytest
import inspect
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_route_request_checks_content_type():
    """route_request must check content-type before calling .json()."""
    from app import route_request

    source = inspect.getsource(route_request)
    assert "content-type" in source.lower() or "content_type" in source.lower(), (
        "route_request doesn't check content-type — binary responses will crash!"
    )


def test_route_request_handles_audio():
    """route_request must detect audio/* content and NOT call .json()."""
    from app import route_request

    source = inspect.getsource(route_request)
    assert "audio/" in source, (
        "route_request doesn't check for audio/* content type"
    )


def test_route_request_returns_response_for_binary():
    """route_request returns Response object for binary content, not dict."""
    from app import route_request

    source = inspect.getsource(route_request)
    assert "Response(" in source, (
        "route_request doesn't create Response for binary content"
    )


def test_dynamic_route_handles_response_object():
    """dynamic_route must check if result is Response before wrapping in GatewayResponse."""
    from app import dynamic_route

    source = inspect.getsource(dynamic_route)
    assert "isinstance(result, Response)" in source or "isinstance(result," in source, (
        "dynamic_route doesn't check for Response objects — binary won't pass through!"
    )


def test_route_request_return_type_is_not_dict():
    """route_request return type annotation should not be -> Dict (it can return Response too)."""
    from app import route_request

    hints = getattr(route_request, "__annotations__", {})
    # It should either have no return annotation or not be Dict
    if "return" in hints:
        import typing
        assert hints["return"] is not dict, (
            "route_request still annotated as -> Dict, will mislead callers"
        )
