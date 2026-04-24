"""
FIRE Planner agent — corpus, SIP gap, blended return from allocation, sensitivity table.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.agents.state import FinancialState
from app.core.agent_envelope import wrap_agent_response
from app.core.llm import primary_llm
from app.database import AsyncSessionLocal

_FIRE_PROMPT = """You are a FIRE (Financial Independence Retire Early) expert for Indian investors.
Given the calculations below, provide a concise FIRE plan with:
1. Whether the user is on track or behind
2. Key actions to accelerate FIRE (max 3)
3. Tax-saving opportunities they're missing
4. Insurance gaps

Data:
{data}

Be specific with ₹ amounts and timelines."""


def compute_blended_return(portfolio_data: dict | None, assumptions: dict[str, float]) -> float:
    """Weight expected return by current allocation; else equity large-cap default."""
    if not portfolio_data or not portfolio_data.get("funds"):
        return float(assumptions["equity_lc_return"])
    schemes = portfolio_data["funds"]
    total_value = sum(float(s.get("current_value") or 0) for s in schemes)
    if total_value <= 0:
        return float(assumptions["equity_lc_return"])
    blended = 0.0
    rate_map = {
        "large_cap": assumptions["equity_lc_return"],
        "mid_cap": assumptions["equity_mc_return"],
        "small_cap": assumptions["equity_sc_return"],
        "debt": assumptions["debt_return"],
        "corporate_debt": assumptions["debt_return"],
        "short_debt": assumptions["debt_return"],
        "liquid": assumptions["debt_return"],
        "gilt": assumptions["debt_return"],
        "hybrid": (assumptions["equity_lc_return"] + assumptions["debt_return"]) / 2,
    }
    for scheme in schemes:
        weight = float(scheme.get("current_value") or 0) / total_value
        category = scheme.get("category") or "large_cap"
        rate = float(rate_map.get(category, assumptions["equity_lc_return"]))
        blended += weight * rate
    return blended


def _fire_corpus_nominal(
    annual_expenses: float,
    inflation_rate: float,
    years: int,
    withdrawal_rate: float = 0.04,
) -> float:
    future = annual_expenses * ((1 + inflation_rate) ** max(years, 1))
    return future / withdrawal_rate


def _fv_corpus(current_corpus: float, real_return: float, years: int) -> float:
    return current_corpus * ((1 + real_return) ** max(years, 1))


def _required_sip_monthly(gap_nominal: float, real_monthly: float, months: int) -> float:
    if gap_nominal <= 0 or months <= 0:
        return 0.0
    r = real_monthly
    if r <= 0:
        return gap_nominal / months
    return gap_nominal * r / (((1 + r) ** months) - 1)


async def run(state: FinancialState) -> dict[str, Any]:
    from app.agents.profile_checks import require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}
    portfolio_data = state.get("portfolio_data")

    income = profile.get("monthly_income")
    expenses = profile.get("monthly_expenses")
    age = profile.get("age")
    fire_target_age = profile.get("fire_target_age")

    async with AsyncSessionLocal() as db:
        from app.core.assumptions import get_user_assumptions

        assumptions = await get_user_assumptions(db, state["user_id"])

    inflation_rate = float(assumptions["inflation_rate"])
    sip_stepup = float(assumptions["sip_stepup_pct"])
    blended = compute_blended_return(portfolio_data, assumptions)
    real_return = max(blended - inflation_rate, 0.01)

    savings = profile.get("savings") or 0
    epf = profile.get("epf_balance") or 0
    nps = profile.get("nps_balance") or 0
    ppf = profile.get("ppf_balance") or 0

    annual_expenses = float(expenses) * 12
    years_to_fire = max(int(fire_target_age) - int(age), 1)
    fire_corpus_required = _fire_corpus_nominal(annual_expenses, inflation_rate, years_to_fire)

    current_corpus = float((portfolio_data or {}).get("current_value") or 0) + savings + epf + nps + ppf

    fv_current = _fv_corpus(current_corpus, real_return, years_to_fire)
    gap = max(fire_corpus_required - fv_current, 0)
    months = years_to_fire * 12
    monthly_r = real_return / 12
    required_sip = _required_sip_monthly(gap, monthly_r, months)
    current_sip = float(income) - float(expenses)
    sip_gap = max(required_sip - max(current_sip, 0), 0)

    retire_year = date.today().year + years_to_fire

    sensitivity = []
    for delta in (-0.02, 0.0, 0.02):
        br = blended + delta
        r_eff = max(br - inflation_rate, 0.01)
        fc = _fire_corpus_nominal(annual_expenses, inflation_rate, years_to_fire)
        fv = _fv_corpus(current_corpus, r_eff, years_to_fire)
        projected_end = fv
        rs = _required_sip_monthly(max(fc - fv, 0), r_eff / 12, months)
        sensitivity.append(
            {
                "return_pct": round(br, 4),
                "corpus": round(projected_end),
                "retire_year": retire_year,
                "monthly_sip_required": round(rs),
            }
        )

    roadmap = []
    projected = current_corpus
    m_sip = max(current_sip, 0)
    for m in range(1, min(months, 36) + 1):
        projected = projected * (1 + monthly_r) + m_sip
        roadmap.append({"month": m, "corpus": round(projected), "sip": round(m_sip)})
        if m % 12 == 0:
            m_sip *= 1 + sip_stepup

    investments_80c = profile.get("investments_80c") or profile.get("section_80c_amount") or 0
    nps_contribution = profile.get("nps_contribution") or 0
    tax_gaps = []
    if investments_80c < 150000:
        tax_gaps.append(f"80C: ₹{150000 - investments_80c:,.0f} unused of ₹1.5L limit")
    if nps_contribution < 50000:
        tax_gaps.append(
            f"80CCD(1B): ₹{50000 - nps_contribution:,.0f} additional NPS deduction available"
        )
    if not profile.get("has_health_insurance"):
        tax_gaps.append("80D: No health insurance — missing ₹25,000 deduction + health coverage")

    insurance_gaps = []
    life_cover = profile.get("life_insurance_cover") or 0
    recommended_cover = float(income) * 12 * 15
    if life_cover < recommended_cover:
        insurance_gaps.append(
            f"Term life: ₹{(recommended_cover - life_cover):,.0f} additional cover needed "
            "(target: 15x annual income)"
        )

    inner = {
        "fire_corpus_required": round(fire_corpus_required),
        "current_corpus": round(current_corpus),
        "corpus_gap": round(max(fire_corpus_required - fv_current, 0)),
        "years_to_retire": years_to_fire,
        "retire_year": retire_year,
        "monthly_sip_required": round(required_sip),
        "current_monthly_sip": round(current_sip),
        "sip_gap": round(sip_gap),
        "insurance_gap": round(max(recommended_cover - life_cover, 0)),
        "blended_return_used": round(blended, 4),
        "sensitivity": sensitivity,
        "monthly_roadmap": roadmap,
        "tax_gaps": tax_gaps,
        "insurance_gaps": insurance_gaps,
    }

    try:
        result = await primary_llm.ainvoke(_FIRE_PROMPT.format(data=str(inner)))
        inner["advice"] = result.content.strip()
    except Exception:
        inner["advice"] = ""

    assumptions_used = {
        "inflation_rate": inflation_rate,
        "equity_return": assumptions["equity_lc_return"],
        "sip_stepup_pct": sip_stepup,
    }
    out = wrap_agent_response(
        "fire_planner",
        "success",
        "live",
        assumptions_used,
        inner,
    )
    out["data_quality"] = "live"
    return out


async def run_fire_planner(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id,
        "message": "FIRE plan",
        "intent": "fire_planner",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    inner = (
        output.get("output", output)
        if isinstance(output, dict) and "output" in output
        else output
    )
    response = await synthesize(inner, "fire_planner", "FIRE plan", language, voice_mode)
    return {"analysis": inner, "response": response, "envelope": output}
