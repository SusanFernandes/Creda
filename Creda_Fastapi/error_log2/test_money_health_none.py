"""
test_money_health_none.py — Regression test for money_health_agent NoneType crash.

BUG (error_log2):
  profile.get("expenses", income * 0.7) returns None when the profile
  has {"expenses": None} explicitly stored. Then `expenses * 6` crashes
  with TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'.

FIX:
  Changed all profile.get() calls to use `or` pattern:
    expenses = profile.get("expenses") or (income * 0.7)
  This handles both missing keys AND explicit None values.
"""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_state(profile=None, portfolio=None):
    """Build minimal FinancialState dict for testing."""
    return {
        "user_profile": profile or {},
        "portfolio_data": portfolio or {},
    }


def test_money_health_with_none_expenses():
    """REGRESSION: expenses=None must not crash (was TypeError: None * 6)."""
    from agents.money_health_agent import money_health_score_agent

    state = _make_state(profile={
        "income": 100000,
        "expenses": None,    # <-- explicit None, not missing
        "savings": 50000,
    })
    result = money_health_score_agent(state)
    assert "agent_outputs" in result
    health = result["agent_outputs"]["money_health"]
    assert "overall_score" in health
    assert isinstance(health["overall_score"], (int, float))


def test_money_health_with_none_income():
    """income=None should default to 1, not crash."""
    from agents.money_health_agent import money_health_score_agent

    state = _make_state(profile={
        "income": None,
        "expenses": None,
        "savings": None,
    })
    result = money_health_score_agent(state)
    health = result["agent_outputs"]["money_health"]
    assert health["overall_score"] >= 0


def test_money_health_with_empty_profile():
    """Empty profile must use defaults throughout without crash."""
    from agents.money_health_agent import money_health_score_agent

    state = _make_state(profile={})
    result = money_health_score_agent(state)
    health = result["agent_outputs"]["money_health"]
    assert health["grade"] in ("A", "B", "C", "D")
    assert len(health["dimensions"]) == 6


def test_money_health_all_values_present():
    """Fully populated profile still works correctly."""
    from agents.money_health_agent import money_health_score_agent

    state = _make_state(profile={
        "income": 200000,
        "expenses": 80000,
        "savings": 1000000,
        "emergency_fund": 480000,
        "life_insurance_cover": 36000000,
        "has_health_insurance": True,
        "monthly_emi": 30000,
        "investments_80c": 150000,
        "age": 35,
    })
    result = money_health_score_agent(state)
    health = result["agent_outputs"]["money_health"]
    assert health["overall_score"] > 0


def test_money_health_none_emergency_fund():
    """emergency_fund=None should not crash."""
    from agents.money_health_agent import money_health_score_agent

    state = _make_state(profile={
        "income": 100000,
        "expenses": 60000,
        "savings": 200000,
        "emergency_fund": None,
    })
    result = money_health_score_agent(state)
    assert "agent_outputs" in result


def test_money_health_none_age():
    """age=None should default to 30."""
    from agents.money_health_agent import money_health_score_agent

    state = _make_state(profile={"age": None})
    result = money_health_score_agent(state)
    health = result["agent_outputs"]["money_health"]
    rr = health["dimensions"]["retirement_readiness"]
    assert rr["years_left"] == 30  # 60 - 30
