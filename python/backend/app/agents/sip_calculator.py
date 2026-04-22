"""
SIP Calculator agent — monthly SIP, step-up SIP, lumpsum + SIP combos.
"""
import math
from typing import Any

from app.agents.state import FinancialState


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    message = state.get("message", "")

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    available = income - expenses

    # Extract target from message or use defaults
    target = _extract_target(message) or income * 12 * 25  # 25x annual income
    years = _extract_years(message) or 20
    annual_return = 0.12
    step_up_pct = 0.10

    monthly_return = annual_return / 12
    months = years * 12

    # Basic SIP
    if monthly_return > 0 and months > 0:
        basic_sip = target * monthly_return / (((1 + monthly_return) ** months) - 1)
    else:
        basic_sip = target / max(months, 1)

    # Step-up SIP (10% annual increase)
    step_up_corpus = _step_up_sip_fv(available, step_up_pct, annual_return, years)

    # How much you'd accumulate with current savings
    current_fv = _sip_fv(available, annual_return, years)

    return {
        "target_corpus": round(target),
        "years": years,
        "expected_return": annual_return * 100,
        "basic_sip_needed": round(basic_sip),
        "step_up_sip": {
            "starting_amount": available,
            "annual_increase": f"{step_up_pct * 100:.0f}%",
            "corpus_at_end": round(step_up_corpus),
        },
        "current_savings_projection": {
            "monthly_sip": available,
            "corpus_in_{years}_years": round(current_fv),
            "meets_target": current_fv >= target,
        },
        "sip_affordable": basic_sip <= available,
        "shortfall": round(max(basic_sip - available, 0)),
    }


def _sip_fv(monthly: float, annual_return: float, years: int) -> float:
    """Future value of a regular SIP."""
    r = annual_return / 12
    n = years * 12
    if r == 0:
        return monthly * n
    return monthly * (((1 + r) ** n) - 1) / r * (1 + r)


def _step_up_sip_fv(starting_monthly: float, annual_increase: float,
                     annual_return: float, years: int) -> float:
    """Future value of SIP with annual step-up."""
    total = 0
    monthly = starting_monthly
    for year in range(years):
        remaining_years = years - year
        fv = _sip_fv(monthly, annual_return, 1) * ((1 + annual_return) ** (remaining_years - 1))
        total += fv
        monthly *= (1 + annual_increase)
    return total


def _extract_target(message: str) -> float | None:
    import re
    # Look for amounts like "1 crore", "50 lakh", "₹10,00,000"
    cr_match = re.search(r"(\d+\.?\d*)\s*(?:cr|crore)", message, re.I)
    if cr_match:
        return float(cr_match.group(1)) * 10_000_000
    lakh_match = re.search(r"(\d+\.?\d*)\s*(?:l|lakh|lac)", message, re.I)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000
    return None


def _extract_years(message: str) -> int | None:
    import re
    match = re.search(r"(\d+)\s*(?:year|yr)", message, re.I)
    return int(match.group(1)) if match else None
