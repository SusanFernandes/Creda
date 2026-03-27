"""
test_money_health_422.py — Regression test for /money-health-score 422 error.

BUG (error_app_py.log):
  Frontend sent: {age: 32, income: 800000, savings: 250000, ...}  ← NO user_id
  Backend requires: MoneyHealthRequest(user_id: str, language: str)
  Result: 422 Unprocessable Entity (repeated 12 times in logs)

FIX:
  - Backend: MoneyHealthRequest.user_id now defaults to "anonymous"
  - Frontend: api.ts getHealthScore() always sends user_id

This test ensures /money-health-score NEVER 422s for missing user_id again.
"""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """Create async client for finance service."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from fastapi2_finance import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────
# THE BUG: Missing user_id caused 422
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_money_health_without_user_id(client: AsyncClient):
    """
    REGRESSION: sending a request WITHOUT user_id must NOT 422.
    The exact payload from the error log that caused the 422.
    """
    # This is the EXACT payload from the error log:
    payload = {
        "age": 32,
        "income": 800000,
        "savings": 250000,
        "dependents": 1,
        "risk_tolerance": 3,
        "goal_type": "retirement",
        "time_horizon": 25,
    }
    resp = await client.post("/money-health-score", json=payload)
    # Must NOT be 422 — user_id should default to "anonymous"
    assert resp.status_code != 422, (
        f"Still getting 422! Response: {resp.text}"
    )


@pytest.mark.asyncio
async def test_money_health_with_user_id(client: AsyncClient):
    """Sending a request WITH user_id should always work."""
    payload = {
        "user_id": "test_user_123",
        "language": "en",
    }
    resp = await client.post("/money-health-score", json=payload)
    assert resp.status_code != 422, (
        f"422 even WITH user_id! Response: {resp.text}"
    )


@pytest.mark.asyncio
async def test_money_health_empty_body(client: AsyncClient):
    """Even a completely empty body should work (all fields have defaults)."""
    resp = await client.post("/money-health-score", json={})
    assert resp.status_code != 422, (
        f"Empty body caused 422! Response: {resp.text}"
    )


@pytest.mark.asyncio
async def test_money_health_with_language(client: AsyncClient):
    """user_id defaults, language explicit."""
    resp = await client.post("/money-health-score", json={"language": "hi"})
    assert resp.status_code != 422


# ──────────────────────────────────────────────────────────────────────────
# STRUCTURAL VALIDATION
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_money_health_response_is_json(client: AsyncClient):
    """Response should always be JSON, never an error page."""
    resp = await client.post("/money-health-score", json={"user_id": "test"})
    assert resp.headers.get("content-type", "").startswith("application/json"), (
        f"Expected JSON, got: {resp.headers.get('content-type')}"
    )
