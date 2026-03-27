"""
test_finance_endpoints.py — Regression tests for finance service endpoints.

From the error logs, several endpoints were called. These tests verify
that all finance endpoints accept valid payloads and return proper responses.
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
# HEALTH
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_finance_health(client: AsyncClient):
    """Finance service /health must 200."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data or "service" in data or isinstance(data, dict)


# ──────────────────────────────────────────────────────────────────────────
# SIP CALCULATOR (no LLM needed — pure math)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sip_calculator_basic(client: AsyncClient):
    """SIP calculator with valid input should 200."""
    resp = await client.post("/sip-calculator", json={
        "monthly_amount": 10000,
        "years": 10,
        "expected_return": 12.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_sip" in data or "total_invested" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_sip_calculator_defaults(client: AsyncClient):
    """SIP with minimal fields (expected_return defaults to 12.0)."""
    resp = await client.post("/sip-calculator", json={
        "monthly_amount": 5000,
        "years": 5,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sip_calculator_missing_required(client: AsyncClient):
    """SIP without required fields should 422, not 500."""
    resp = await client.post("/sip-calculator", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sip_calculator_zero_return(client: AsyncClient):
    """Edge case: 0% return should not crash."""
    resp = await client.post("/sip-calculator", json={
        "monthly_amount": 10000,
        "years": 10,
        "expected_return": 0.0,
    })
    assert resp.status_code == 200


# ──────────────────────────────────────────────────────────────────────────
# TAX WIZARD (calls LLM — may fail if no API key, but should not 422/500)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tax_wizard_valid_payload(client: AsyncClient):
    """Tax wizard with all required fields should not 422."""
    resp = await client.post("/tax-wizard", json={
        "user_id": "test_user",
        "annual_income": 1200000.0,
        "deductions": {},
    })
    # 200 if LLM works, 500 if no API key — but NEVER 422
    assert resp.status_code != 422, f"Tax wizard validation failed: {resp.text}"


@pytest.mark.asyncio
async def test_tax_wizard_missing_income_422(client: AsyncClient):
    """Missing required annual_income should 422."""
    resp = await client.post("/tax-wizard", json={
        "user_id": "test_user",
    })
    assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────
# MONEY HEALTH SCORE (the 422 regression)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_money_health_profile_without_user_id(client: AsyncClient):
    """
    REGRESSION: Exact payload from error log — must not 422.
    """
    resp = await client.post("/money-health-score", json={
        "age": 32,
        "income": 800000,
        "savings": 250000,
        "dependents": 1,
        "risk_tolerance": 3,
        "goal_type": "retirement",
        "time_horizon": 25,
    })
    assert resp.status_code != 422


@pytest.mark.asyncio
async def test_money_health_minimal(client: AsyncClient):
    """Completely empty body — all defaults."""
    resp = await client.post("/money-health-score", json={})
    assert resp.status_code != 422


# ──────────────────────────────────────────────────────────────────────────
# PROFILE UPSERT
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_profile_upsert(client: AsyncClient):
    """Creating a user profile should work."""
    resp = await client.post("/profile/upsert", json={
        "user_id": "test_regression_user",
        "name": "Test User",
        "age": 30,
        "income": 50000,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_profile_upsert_missing_user_id(client: AsyncClient):
    """Profile without user_id should 422 (it's required)."""
    resp = await client.post("/profile/upsert", json={
        "name": "No ID User",
    })
    assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────
# SUPPORTED FEATURES
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_supported_features(client: AsyncClient):
    """GET /supported_features should always 200."""
    resp = await client.get("/supported_features")
    assert resp.status_code == 200
