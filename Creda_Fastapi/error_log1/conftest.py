"""
conftest.py — Shared fixtures for error_log1 regression tests.

Spins up TestClient instances for each FastAPI service so tests
can hit real endpoints without running separate server processes.
"""

import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

# Ensure the Creda_Fastapi directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ──────────────────────────────────────────────────────────────────────────
# Gateway app (app.py — port 8080 in production)
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def gateway_app():
    """Import and return the gateway FastAPI app."""
    from app import app
    return app


# ──────────────────────────────────────────────────────────────────────────
# Finance service (fastapi2_finance.py — port 8001 in production)
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def finance_app():
    """Import and return the finance FastAPI app."""
    from fastapi2_finance import app
    return app


# ──────────────────────────────────────────────────────────────────────────
# Multilingual service (fastapi1_multilingual.py — port 8000 in production)
# NOTE: This service has heavy model loading in its lifespan. Tests that
# need it should be marked with @pytest.mark.slow so they can be skipped
# in quick CI runs.
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def multilingual_app():
    """Import and return the multilingual FastAPI app."""
    from fastapi1_multilingual import app
    return app


# ──────────────────────────────────────────────────────────────────────────
# Async HTTP clients (for pytest-asyncio tests)
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture
async def finance_client(finance_app):
    """Async test client for the finance service."""
    transport = ASGITransport(app=finance_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def multilingual_client(multilingual_app):
    """Async test client for the multilingual service."""
    transport = ASGITransport(app=multilingual_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
