"""
Money Health Score agent — dimensions + correlation-aware diversification via fund holdings overlap.
"""
from __future__ import annotations

from typing import Any

from app.agents.state import FinancialState
from app.core.agent_envelope import wrap_agent_response
from app.core.llm import primary_llm
from app.database import AsyncSessionLocal

_HEALTH_PROMPT = """You are a financial health assessor for Indian users.
Given these health dimension scores, provide the top 3 specific actions to improve the weakest areas.

Scores:
{scores}

Overall: {grade} ({overall}/100)

Be specific with ₹ amounts and actionable steps. Prioritise the lowest-scoring dimensions."""


def score_diversification(schemes: list[dict[str, Any]], overlaps: list[dict[str, Any]]) -> float:
    """0–100: penalise high pairwise overlap (combined weights)."""
    if len(schemes) < 2:
        return 50.0
    if not overlaps:
        return 100.0
    max_overlap = max((o["weight_a"] + o["weight_b"]) for o in overlaps)
    return max(0.0, 100.0 - (max_overlap / 0.30) * 100.0)


async def run(state: FinancialState) -> dict[str, Any]:
    from app.agents.profile_checks import require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    income = profile.get("monthly_income")
    expenses = profile.get("monthly_expenses")
    emergency = profile.get("emergency_fund") or 0
    life_cover = profile.get("life_insurance_cover") or 0
    has_health = profile.get("has_health_insurance") or False
    monthly_emi = profile.get("monthly_emi") or 0
    investments_80c = profile.get("investments_80c") or profile.get("section_80c_amount") or 0
    fire_target = profile.get("fire_corpus_target") or 0
    age = profile.get("age")

    funds = (portfolio.get("funds") or []) if portfolio else []
    portfolio_value = portfolio.get("current_value") or 0 if portfolio else 0

    overlaps: list[dict[str, Any]] = []
    async with AsyncSessionLocal() as db:
        from app.core.holdings_db import compute_overlap

        isins = [f.get("isin") for f in funds if f.get("isin")]
        if len(isins) >= 2:
            overlaps = await compute_overlap(isins, db)

    scores: dict[str, Any] = {}

    inc = float(income or 0)
    exp = float(expenses or 0)

    target_emergency = exp * 6 if exp else 0
    if target_emergency > 0:
        scores["emergency_preparedness"] = {
            "score": min(round(emergency / target_emergency * 100), 100),
            "weight": 20,
            "detail": f"₹{emergency:,.0f} of ₹{target_emergency:,.0f} target (6 months)",
        }
    else:
        scores["emergency_preparedness"] = {"score": 50, "weight": 20, "detail": "No expense data"}

    annual_income = inc * 12
    recommended_life = annual_income * 15 if annual_income > 0 else 0
    life_score = min(round(life_cover / recommended_life * 100), 100) if recommended_life > 0 else 0
    health_score = 100 if has_health else 0
    scores["insurance_coverage"] = {
        "score": round((life_score * 0.6 + health_score * 0.4)),
        "weight": 20,
        "detail": f"Life: ₹{life_cover:,.0f}/₹{recommended_life:,.0f}, Health: {'Yes' if has_health else 'No'}",
    }

    div_score = score_diversification(funds, overlaps)
    scores["investment_diversification"] = {
        "score": round(div_score),
        "weight": 15,
        "detail": f"{len(funds)} funds, overlap-aware score",
    }

    emi_ratio = (monthly_emi / inc * 100) if inc and inc > 0 else 0
    if emi_ratio == 0:
        debt_score = 100
    elif emi_ratio <= 25:
        debt_score = 90
    elif emi_ratio <= 35:
        debt_score = 70
    elif emi_ratio <= 50:
        debt_score = 40
    else:
        debt_score = 10
    scores["debt_health"] = {
        "score": debt_score,
        "weight": 20,
        "detail": f"EMI/Income ratio: {emi_ratio:.1f}%",
    }

    tax_score = min(round(investments_80c / 150000 * 100), 100) if investments_80c > 0 else 0
    scores["tax_efficiency"] = {
        "score": tax_score,
        "weight": 10,
        "detail": f"80C: ₹{investments_80c:,.0f}/₹1,50,000",
    }

    if fire_target > 0 and portfolio_value > 0:
        ret_score = min(round(portfolio_value / fire_target * 100), 100)
    else:
        target_by_age = annual_income * max((float(age or 30) - 20) / 10, 0.5)
        total_savings = portfolio_value + (profile.get("epf_balance") or 0) + (profile.get("ppf_balance") or 0)
        ret_score = (
            min(round(total_savings / target_by_age * 100), 100) if target_by_age > 0 else 50
        )
    scores["retirement_readiness"] = {
        "score": ret_score,
        "weight": 15,
        "detail": f"Portfolio: ₹{portfolio_value:,.0f}",
    }

    overall = sum(s["score"] * s["weight"] for s in scores.values()) / 100
    overall = round(overall)

    if overall >= 80:
        grade = "A"
    elif overall >= 60:
        grade = "B"
    elif overall >= 40:
        grade = "C"
    else:
        grade = "D"

    try:
        result = await primary_llm.ainvoke(
            _HEALTH_PROMPT.format(scores=str(scores), grade=grade, overall=overall)
        )
        actions = result.content.strip()
    except Exception:
        actions = ""

    inner = {
        "overall_score": overall,
        "grade": grade,
        "dimensions": scores,
        "top_actions": actions,
        "overlap_pairs": len(overlaps),
    }

    dq = "live" if funds else "partial"
    out = wrap_agent_response(
        "money_health",
        "success",
        dq,
        {},
        inner,
    )
    out["data_quality"] = dq
    return out


async def run_money_health(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id,
        "message": "health score",
        "intent": "money_health",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    inner = output.get("output", output) if isinstance(output, dict) else output
    response = await synthesize(inner, "money_health", "health score", language, voice_mode)
    return {"analysis": inner, "response": response}
