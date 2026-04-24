"""
SIP Calculator agent — monthly SIP, step-up SIP, lumpsum + SIP combos.
"""
import math
from typing import Any

from app.agents.profile_checks import profile_incomplete_payload, require_complete_profile
from app.agents.state import FinancialState
from app.database import AsyncSessionLocal


async def run(state: FinancialState) -> dict[str, Any]:
    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}
    message = state.get("message", "")

    income = float(profile["monthly_income"])
    expenses = float(profile["monthly_expenses"])
    available = income - expenses

    target = _extract_target(message) or profile.get("goal_target_amount")
    years = _extract_years(message) or profile.get("goal_target_years")
    if target is None or target == 0:
        return profile_incomplete_payload(
            {"missing": ["goal_target_amount"], "completeness_pct": 75.0, "is_complete": False}
        )
    if years is None or years == 0:
        return profile_incomplete_payload(
            {"missing": ["goal_target_years"], "completeness_pct": 80.0, "is_complete": False}
        )

    async with AsyncSessionLocal() as db:
        from app.core.assumptions import get_user_assumptions

        assumptions = await get_user_assumptions(db, state["user_id"])

    annual_return = float(assumptions["equity_lc_return"])
    step_up_pct = float(assumptions["sip_stepup_pct"])

    monthly_return = annual_return / 12
    months = int(years) * 12

    if monthly_return > 0 and months > 0:
        basic_sip = target * monthly_return / (((1 + monthly_return) ** months) - 1)
    else:
        basic_sip = target / max(months, 1)

    step_up_corpus = _step_up_sip_fv(available, step_up_pct, annual_return, int(years))
    current_fv = _sip_fv(available, annual_return, int(years))

    return {
        "target_corpus": round(target),
        "years": int(years),
        "expected_return": annual_return * 100,
        "basic_sip_needed": round(basic_sip),
        "step_up_sip": {
            "starting_amount": available,
            "annual_increase": f"{step_up_pct * 100:.0f}%",
            "corpus_at_end": round(step_up_corpus),
        },
        "current_savings_projection": {
            "monthly_sip": available,
            f"corpus_in_{int(years)}_years": round(current_fv),
            "meets_target": current_fv >= target,
        },
        "sip_affordable": basic_sip <= available,
        "shortfall": round(max(basic_sip - available, 0)),
        "data_quality": "live",
        "assumptions_used": {
            "equity_return": annual_return,
            "sip_stepup_pct": step_up_pct,
        },
    }


def _sip_fv(monthly: float, annual_return: float, years: int) -> float:
    """Future value of a regular SIP."""
    r = annual_return / 12
    n = years * 12
    if r == 0:
        return monthly * n
    return monthly * (((1 + r) ** n) - 1) / r * (1 + r)


def _step_up_sip_fv(
    starting_monthly: float,
    annual_increase: float,
    annual_return: float,
    years: int,
) -> float:
    """Future value of SIP with annual step-up."""
    total = 0
    monthly = starting_monthly
    for year in range(years):
        remaining_years = years - year
        fv = _sip_fv(monthly, annual_return, 1) * ((1 + annual_return) ** (remaining_years - 1))
        total += fv
        monthly *= 1 + annual_increase
    return total


def _extract_target(message: str) -> float | None:
    import re

    cr_match = re.search(r"(\d+\.?\d*)\s*(?:cr|crore)", message, re.I)
    if cr_match:
        return float(cr_match.group(1)) * 10_000_000
    lakh_match = re.search(r"(\d+\.?\d*)\s*(?:l|lakh|lac)", message, re.I)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000
    raw = re.search(r"target\s+([\d,.]+)", message, re.I)
    if raw:
        return float(raw.group(1).replace(",", ""))
    return None


def _extract_years(message: str) -> int | None:
    import re

    match = re.search(r"(\d+)\s*(?:year|yr)", message, re.I)
    return int(match.group(1)) if match else None
