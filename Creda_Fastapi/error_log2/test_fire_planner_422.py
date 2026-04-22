"""
test_fire_planner_422.py — Regression test for /fire-planner 422 error.

BUG (error_log2):
  Frontend sends FIRERequest {user_id, monthly_expenses, current_savings, ...}
  but /fire-planner accepted ChatRequest which requires `message: str`.
  Result: 422 "Field required" for `message`.

FIX:
  Created FIREPlannerRequest model that accepts both ChatRequest format
  and frontend FIRERequest format (monthly_expenses, current_savings, etc.).
"""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_fire_planner_request_model_accepts_frontend_format():
    """FIREPlannerRequest must accept frontend fields without requiring `message`."""
    from fastapi2_finance import FIREPlannerRequest

    req = FIREPlannerRequest(
        user_id="web_user",
        monthly_expenses=30000,
        current_savings=500000,
        monthly_investment=20000,
        expected_return=12.0,
        inflation_rate=6.0,
    )
    assert req.user_id == "web_user"
    assert req.monthly_expenses == 30000
    assert req.message is None  # Not required


def test_fire_planner_request_model_accepts_chat_format():
    """FIREPlannerRequest must also accept the old ChatRequest format."""
    from fastapi2_finance import FIREPlannerRequest

    req = FIREPlannerRequest(
        message="Plan my FIRE journey",
        user_id="test_user",
    )
    assert req.message == "Plan my FIRE journey"
    assert req.monthly_expenses is None


def test_fire_planner_request_model_defaults():
    """FIREPlannerRequest must have sensible defaults."""
    from fastapi2_finance import FIREPlannerRequest

    req = FIREPlannerRequest()
    assert req.user_id == "anonymous"
    assert req.language == "en"
    assert req.message is None
    assert req.monthly_expenses is None


def test_fire_planner_request_no_required_fields():
    """FIREPlannerRequest must not require any field (all have defaults)."""
    from fastapi2_finance import FIREPlannerRequest

    # This should not raise
    req = FIREPlannerRequest(**{})
    assert req.user_id == "anonymous"
