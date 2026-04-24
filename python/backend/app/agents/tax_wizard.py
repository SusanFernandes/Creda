"""
Tax Wizard — Old vs New regime (FY2025–26 style), HRA, 80D, 80CCD(1B), missed deductions.
"""
from __future__ import annotations

from typing import Any

from app.agents.state import FinancialState
from app.core.agent_envelope import wrap_agent_response
from app.core.llm import primary_llm

_OLD_SLABS = [(250000, 0), (500000, 0.05), (1000000, 0.20), (float("inf"), 0.30)]
_NEW_SLABS = [(300000, 0), (700000, 0.05), (1000000, 0.10), (1200000, 0.15), (1500000, 0.20), (float("inf"), 0.30)]

_TAX_PROMPT = """You are an Indian tax expert (FY2025–26). Given these calculations, provide:
1. Which regime is better and by how much
2. Missed deductions the user should claim
3. One actionable step to save more tax next year

Data:
{data}

Be specific with ₹ amounts. Mention exact section numbers (80C, 80D, etc.)."""


def compute_hra_exemption(
    basic_salary_monthly: float,
    rent_paid_monthly: float,
    hra_received_monthly: float,
    is_metro: bool,
) -> float:
    """Annual HRA exemption (salary-style inputs, monthly)."""
    if rent_paid_monthly == 0:
        return 0.0
    actual_hra = hra_received_monthly * 12
    rent_minus_10pct = max(0.0, rent_paid_monthly * 12 - 0.10 * basic_salary_monthly * 12)
    metro_cap = (0.50 if is_metro else 0.40) * basic_salary_monthly * 12
    return float(min(actual_hra, rent_minus_10pct, metro_cap))


def compute_80d(self_premium: float, parents_premium: float, parents_above_60: bool) -> float:
    self_limit = 25000.0
    parents_limit = 50000.0 if parents_above_60 else 25000.0
    return float(min(self_premium, self_limit) + min(parents_premium, parents_limit))


def _compute_tax(taxable: float, slabs: list[tuple[float, float]]) -> float:
    tax = 0.0
    prev = 0.0
    for limit, rate in slabs:
        if taxable <= prev:
            break
        bracket = min(taxable, limit) - prev
        tax += bracket * rate
        prev = limit
    return tax


async def run(state: FinancialState) -> dict[str, Any]:
    from app.agents.profile_checks import require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}

    income = float(profile["monthly_income"]) * 12
    investments_80c = float(profile.get("section_80c_amount") or profile.get("investments_80c") or 0)
    nps_contribution = float(profile.get("nps_contribution") or 0)
    self_health = float(profile.get("self_health_premium") or profile.get("health_insurance_premium") or 0)
    parents_health = float(profile.get("parents_health_premium") or 0)
    parents_above_60 = bool(profile.get("parents_age_above_60"))
    basic_monthly = float(profile.get("basic_salary") or 0)
    rent_monthly = float(profile.get("rent_paid") or 0)
    hra_monthly = float(profile.get("hra") or 0)
    is_metro = bool(profile.get("is_metro"))
    home_loan_interest = float(profile.get("home_loan_interest") or 0)
    lta_amount = float(profile.get("lta_amount") or 0)

    eighty_d = compute_80d(self_health, parents_health, parents_above_60)
    nps_80ccd1b = min(nps_contribution, 50000.0)

    deduction_hra = compute_hra_exemption(basic_monthly, rent_monthly, hra_monthly, is_metro)

    deduction_80c = min(investments_80c, 150000)
    deduction_24b = min(home_loan_interest, 200000)

    standard_deduction_old = 50000.0
    standard_deduction_new = 75000.0

    total_deductions_old = (
        deduction_80c + eighty_d + nps_80ccd1b + deduction_hra + deduction_24b + lta_amount + standard_deduction_old
    )
    taxable_old = max(income - total_deductions_old, 0)
    tax_old = _compute_tax(taxable_old, _OLD_SLABS)
    if taxable_old <= 500000:
        tax_old = 0

    taxable_new = max(income - standard_deduction_new, 0)
    tax_new = _compute_tax(taxable_new, _NEW_SLABS)
    if taxable_new <= 700000:
        tax_new = 0

    tax_old_total = round(tax_old * 1.04)
    tax_new_total = round(tax_new * 1.04)

    recommended = "old" if tax_old_total < tax_new_total else "new"
    saving = abs(tax_old_total - tax_new_total)

    effective_rate_old = round((tax_old_total / income * 100), 1) if income > 0 else 0
    effective_rate_new = round((tax_new_total / income * 100), 1) if income > 0 else 0

    missed: list[dict[str, Any]] = []
    if investments_80c < 150000:
        missed.append(
            {
                "section": "80C",
                "description": "Section 80C investments",
                "max_benefit": round((150000 - investments_80c) * 0.30),
                "action": "Use ELSS/PPF/NPS Tier 2 within ₹1.5L limit",
                "eligible": True,
                "currently_claimed": investments_80c > 0,
            }
        )
    if nps_80ccd1b < 50000 and profile.get("has_nps"):
        missed.append(
            {
                "section": "80CCD(1B)",
                "description": "Extra NPS deduction",
                "max_benefit": 15000,
                "action": "Invest ₹50,000 in NPS Tier 1",
                "eligible": True,
                "currently_claimed": nps_80ccd1b > 0,
            }
        )

    inner = {
        "gross_income": income,
        "old_regime_tax": tax_old_total,
        "new_regime_tax": tax_new_total,
        "recommended_regime": recommended,
        "annual_saving": saving,
        "effective_rate_old": effective_rate_old,
        "effective_rate_new": effective_rate_new,
        "deductions_breakdown": {
            "80c": deduction_80c,
            "80d": eighty_d,
            "hra": deduction_hra,
            "nps": nps_80ccd1b,
            "standard_old": standard_deduction_old,
            "standard_new": standard_deduction_new,
            "home_loan": deduction_24b,
            "lta": lta_amount,
            "total_old": total_deductions_old,
        },
        "missed_deductions": missed,
    }

    try:
        result = await primary_llm.ainvoke(_TAX_PROMPT.format(data=str(inner)))
        inner["advice"] = result.content.strip()
    except Exception:
        inner["advice"] = ""

    out = wrap_agent_response(
        "tax_wizard",
        "success",
        "live",
        {"data_source": "profile"},
        inner,
    )
    out["data_quality"] = "live"
    return out


async def run_tax_wizard(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id,
        "message": "tax analysis",
        "intent": "tax_wizard",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    inner = output.get("output", output) if isinstance(output, dict) else output
    response = await synthesize(inner, "tax_wizard", "tax analysis", language, voice_mode)
    return {"analysis": inner, "response": response}
