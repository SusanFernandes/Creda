"""
test_missing_endpoints.py — Regression test for 404 missing endpoints.

BUG (error_log2):
  Frontend called /budget/optimize, /portfolio/optimize, /portfolio/check-rebalance
  but these endpoints didn't exist → 404 Not Found (many times in logs).

FIX:
  Added all three endpoints in fastapi2_finance.py (backend)
  and corresponding gateway proxies in app.py.
  Added ApiService methods in api.ts (frontend).
"""

import pytest
import sys, os, inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Backend endpoint existence ───────────────────────────────────────────

def test_budget_optimize_endpoint_exists():
    """Finance service must have /budget/optimize endpoint."""
    from fastapi2_finance import app
    routes = [r.path for r in app.routes]
    assert "/budget/optimize" in routes, (
        "/budget/optimize endpoint missing from finance service"
    )


def test_portfolio_optimize_endpoint_exists():
    """Finance service must have /portfolio/optimize endpoint."""
    from fastapi2_finance import app
    routes = [r.path for r in app.routes]
    assert "/portfolio/optimize" in routes, (
        "/portfolio/optimize endpoint missing from finance service"
    )


def test_portfolio_check_rebalance_endpoint_exists():
    """Finance service must have /portfolio/check-rebalance endpoint."""
    from fastapi2_finance import app
    routes = [r.path for r in app.routes]
    assert "/portfolio/check-rebalance" in routes, (
        "/portfolio/check-rebalance endpoint missing from finance service"
    )


# ─── Gateway endpoint existence ───────────────────────────────────────────

def test_gateway_budget_optimize_exists():
    """Gateway must have /budget/optimize endpoint."""
    from app import app
    routes = [r.path for r in app.routes]
    assert "/budget/optimize" in routes, (
        "/budget/optimize gateway endpoint missing"
    )


def test_gateway_portfolio_optimize_exists():
    """Gateway must have /portfolio/optimize endpoint."""
    from app import app
    routes = [r.path for r in app.routes]
    assert "/portfolio/optimize" in routes, (
        "/portfolio/optimize gateway endpoint missing"
    )


def test_gateway_portfolio_check_rebalance_exists():
    """Gateway must have /portfolio/check-rebalance endpoint."""
    from app import app
    routes = [r.path for r in app.routes]
    assert "/portfolio/check-rebalance" in routes, (
        "/portfolio/check-rebalance gateway endpoint missing"
    )


# ─── Route list includes new endpoints ───────────────────────────────────

def test_finance_routes_include_new_endpoints():
    """determine_service_route must know about the new finance endpoints."""
    from app import determine_service_route

    for endpoint in ["/budget/optimize", "/portfolio/optimize", "/portfolio/check-rebalance"]:
        url, service = determine_service_route(endpoint)
        assert service == "finance", (
            f"{endpoint} is not routed to finance service (got {service})"
        )


# ─── Request model validation ────────────────────────────────────────────

def test_budget_optimize_request_model():
    """BudgetOptimizeRequest must accept all frontend params."""
    from fastapi2_finance import BudgetOptimizeRequest

    req = BudgetOptimizeRequest(
        user_id="test",
        expenses=[{"category": "food", "amount": 5000}],
        language="en",
    )
    assert req.user_id == "test"
    assert len(req.expenses) == 1


def test_portfolio_optimize_request_model():
    """PortfolioOptimizeRequest must accept all frontend params."""
    from fastapi2_finance import PortfolioOptimizeRequest

    req = PortfolioOptimizeRequest(
        user_id="test",
        goals=["retirement", "wealth_creation"],
        time_horizon_years=25,
    )
    assert req.goals == ["retirement", "wealth_creation"]
    assert req.time_horizon_years == 25


def test_rebalance_check_request_model():
    """RebalanceCheckRequest must accept profile and threshold params."""
    from fastapi2_finance import RebalanceCheckRequest

    req = RebalanceCheckRequest(
        user_id="test",
        current_allocation={"equity": 0.7, "debt": 0.3},
        threshold=0.05,
    )
    assert req.threshold == 0.05
    assert req.current_allocation["equity"] == 0.7
