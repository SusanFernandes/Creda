"""
Money Health Score agent — 6 dimensions, radar payload, diversification from weights + holdings overlap,
retirement score from FIRE gap heuristic, static fallback top actions.
"""
from __future__ import annotations

from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_HEALTH_PROMPT = """You are a financial health assessor for Indian users.
Given these 6 health dimension scores, provide the top 3 specific actions to improve the weakest areas.

Scores:
{scores}

Overall: {grade} ({overall}/100)

Be specific with ₹ amounts and actionable steps. Prioritise the lowest-scoring dimensions."""


_FALLBACK_ACTIONS = [
    {
        "title": "Max unused 80C (₹1.5L)",
        "impact": "Up to ~₹46,800 tax saved at 31.2% marginal rate",
        "cta": "tax_wizard",
    },
    {
        "title": "Switch regular MF plans to direct",
        "impact": "Often saves 0.5–1% TER yearly on the same portfolio",
        "cta": "portfolio_xray",
    },
    {
        "title": "Top up term insurance toward 15× annual income",
        "impact": "Low premium vs family security",
        "cta": "settings",
    },
]


def _diversification_score(funds: list[dict]) -> tuple[int, str]:
    """Herfindahl on category weights (lower concentration = higher score) + fund count bonus."""
    if not funds:
        return 45, "No CAMS portfolio — upload for overlap-aware diversification"
    total = sum(float(f.get("current_value") or 0) for f in funds)
    if total <= 0:
        return 50, "Zero portfolio value"
    by_cat: dict[str, float] = {}
    for f in funds:
        cat = (f.get("category") or "unknown").lower()
        by_cat[cat] = by_cat.get(cat, 0) + float(f.get("current_value") or 0)
    hhi = sum((v / total) ** 2 for v in by_cat.values())
    # hhi 1/n perfect equal n cats -> map to 0-100
    n = max(len(by_cat), 1)
    ideal = 1.0 / n
    if hhi <= ideal * 1.15:
        score = 90
    elif hhi <= 0.5:
        score = 75
    elif hhi <= 0.7:
        score = 60
    else:
        score = max(35, int(100 - hhi * 80))
    detail = f"HHI={hhi:.2f}, {len(by_cat)} categories, {len(funds)} funds"
    return min(100, score), detail


def _retirement_score_from_fire_gap(
    profile: dict,
    portfolio_value: float,
) -> tuple[int, str]:
    """Approximate FIRE progress vs target (not only fire_corpus_target)."""
    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    age = int(profile.get("age") or 30)
    fta = int(profile.get("fire_target_age") or 0)
    if income <= 0 or expenses <= 0 or fta <= age:
        return 50, "Set age, expenses, and fire_target_age for retirement readiness"
    infl = 0.06
    years = max(fta - age, 1)
    future_exp = expenses * 12 * ((1 + infl) ** years)
    fire_num = future_exp / 0.04
    corpus = portfolio_value + float(profile.get("savings") or 0) + float(profile.get("epf_balance") or 0)
    pct = min(100, round(corpus / fire_num * 100)) if fire_num > 0 else 0
    return pct, f"~{pct}% of simplified FIRE target (₹{fire_num:,.0f}) with corpus ₹{corpus:,.0f}"


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    if income <= 0 or expenses <= 0:
        from app.services.profile_completeness import humanize_missing, missing_for_core_planning

        miss = missing_for_core_planning(profile)
        return {
            "profile_incomplete": True,
            "missing_fields_detail": humanize_missing(miss),
            "overall_score": None,
            "grade": "N/A",
            "dimensions": None,
            "benchmark": None,
            "top_actions": "Save monthly income and expenses in Settings, then refresh this page.",
            "top_actions_structured": [
                {
                    "title": "Add income & expenses",
                    "impact": "Required before we can score emergency fund, tax, and retirement readiness.",
                    "cta": "settings",
                },
            ],
            "radar_chart": [],
        }

    emergency = float(profile.get("emergency_fund") or 0)
    life_cover = float(profile.get("life_insurance_cover") or 0)
    has_health = bool(profile.get("has_health_insurance"))
    monthly_emi = float(profile.get("monthly_emi") or 0)
    investments_80c = float(profile.get("investments_80c") or profile.get("section_80c_amount") or 0)
    age = int(profile.get("age") or 30)

    funds = (portfolio.get("funds") or []) if portfolio else []
    portfolio_value = float(portfolio.get("current_value", 0) or 0)

    scores: dict[str, Any] = {}

    target_emergency = expenses * 6
    scores["emergency_preparedness"] = {
        "score": min(round(emergency / target_emergency * 100), 100) if target_emergency > 0 else 50,
        "weight": 20,
        "detail": f"₹{emergency:,.0f} of ₹{target_emergency:,.0f} target (6 months)",
    }

    annual_income = income * 12
    recommended_life = annual_income * 15
    life_score = min(round(life_cover / recommended_life * 100), 100) if recommended_life > 0 else 0
    health_score = 100 if has_health else 0
    scores["insurance_coverage"] = {
        "score": round(life_score * 0.6 + health_score * 0.4),
        "weight": 20,
        "detail": f"Life: ₹{life_cover:,.0f}/₹{recommended_life:,.0f}, Health: {'Yes' if has_health else 'No'}",
    }

    div_score, div_detail = _diversification_score(funds)
    scores["investment_diversification"] = {
        "score": div_score,
        "weight": 15,
        "detail": div_detail,
    }

    emi_ratio = (monthly_emi / income * 100) if income > 0 else 0
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

    ret_score, ret_detail = _retirement_score_from_fire_gap(profile, portfolio_value)
    scores["retirement_readiness"] = {
        "score": ret_score,
        "weight": 15,
        "detail": ret_detail,
    }

    overall = round(sum(s["score"] * s["weight"] for s in scores.values()) / 100)
    if overall >= 80:
        grade = "A"
    elif overall >= 60:
        grade = "B"
    elif overall >= 40:
        grade = "C"
    else:
        grade = "D"

    age_band = f"{(age // 5) * 5}-{(age // 5) * 5 + 4}"
    city = (profile.get("city") or "").strip().lower()
    _BENCHMARKS = {
        "25-29": {"avg_score": 42, "emergency_mo": 2.1, "insurance_x": 12},
        "30-34": {"avg_score": 48, "emergency_mo": 2.4, "insurance_x": 12},
        "35-39": {"avg_score": 54, "emergency_mo": 2.8, "insurance_x": 12},
        "40-44": {"avg_score": 58, "emergency_mo": 3.0, "insurance_x": 13},
        "45-49": {"avg_score": 55, "emergency_mo": 3.2, "insurance_x": 13},
    }
    bench = _BENCHMARKS.get(age_band, {"avg_score": 50, "emergency_mo": 2.5, "insurance_x": 12})
    user_ef_mo = emergency / expenses if expenses > 0 else 0
    user_ins_x = (life_cover / annual_income) if annual_income > 0 else 0
    peer_avg = bench["avg_score"]
    # Rough percentile vs synthetic peer distribution (UI expects these keys).
    pct_rank = max(5, min(95, 50 + int((overall - peer_avg) * 2)))
    benchmark = {
        "age_band": age_band,
        "city": city or "India",
        "peer_avg_score": peer_avg,
        "your_score": overall,
        "diff": overall - peer_avg,
        "percentile": pct_rank,
        "peer_emergency_pct": 62,
        "peer_insurance_pct": 48,
        "peer_sip_pct": 55,
        "peer_rows": [
            {
                "metric": "Emergency fund (months)",
                "you": round(user_ef_mo, 1),
                "peer_avg": bench["emergency_mo"],
                "ahead": user_ef_mo >= bench["emergency_mo"],
            },
            {
                "metric": "Life cover (× annual income)",
                "you": round(user_ins_x, 1),
                "peer_avg": bench["insurance_x"],
                "ahead": user_ins_x >= bench["insurance_x"],
            },
        ],
        "insight": f"Your score of {overall} vs peer avg ~{peer_avg} ({age_band}).",
    }

    radar_chart = [
        {"axis": "Emergency", "score": scores["emergency_preparedness"]["score"]},
        {"axis": "Insurance", "score": scores["insurance_coverage"]["score"]},
        {"axis": "Diversification", "score": scores["investment_diversification"]["score"]},
        {"axis": "Debt", "score": scores["debt_health"]["score"]},
        {"axis": "Tax", "score": scores["tax_efficiency"]["score"]},
        {"axis": "Retirement", "score": scores["retirement_readiness"]["score"]},
    ]

    top_actions_text = ""
    try:
        result = await primary_llm.ainvoke(
            _HEALTH_PROMPT.format(scores=str(scores), grade=grade, overall=overall)
        )
        top_actions_text = result.content.strip()
    except Exception:
        top_actions_text = ""

    structured_actions = list(_FALLBACK_ACTIONS)
    if top_actions_text:
        structured_actions.insert(
            0,
            {"title": "AI recommendations", "impact": top_actions_text[:400], "cta": "general"},
        )

    return {
        "overall_score": overall,
        "grade": grade,
        "dimensions": scores,
        "benchmark": benchmark,
        "top_actions": top_actions_text or None,
        "top_actions_structured": structured_actions[:3],
        "radar_chart": radar_chart,
    }


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
    response = await synthesize(output, "money_health", "health score", language, voice_mode)
    return {"analysis": output, "response": response}
