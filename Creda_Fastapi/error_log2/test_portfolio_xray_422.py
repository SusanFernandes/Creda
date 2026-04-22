"""
test_portfolio_xray_422.py — Regression test for /portfolio/xray 422 error.

BUG (error_log2):
  Frontend only sends `file` + `user_id` but backend requires `password: str = Form(...)`.
  Result: 422 "Field required" for `password`.

FIX:
  Made `password` optional with `Form(default="")` in both
  gateway (app.py) and finance service (fastapi2_finance.py).
"""

import pytest
import inspect
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_finance_xray_password_optional():
    """Finance service /portfolio/xray must not require password."""
    from fastapi2_finance import portfolio_xray

    sig = inspect.signature(portfolio_xray)
    password_param = sig.parameters.get("password")
    assert password_param is not None, "portfolio_xray missing password param"
    assert password_param.default is not inspect.Parameter.empty, (
        "portfolio_xray password is still required (no default)"
    )


def test_gateway_xray_password_optional():
    """Gateway /portfolio/xray must not require password."""
    from app import gateway_portfolio_xray

    sig = inspect.signature(gateway_portfolio_xray)
    password_param = sig.parameters.get("password")
    assert password_param is not None, "gateway_portfolio_xray missing password param"
    assert password_param.default is not inspect.Parameter.empty, (
        "gateway_portfolio_xray password is still required (no default)"
    )
