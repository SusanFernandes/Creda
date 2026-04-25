"""
Money Health Score agent — 6 dimensions, 0-100 weighted score, grade, top 3 actions.
"""
from typing import Any

from app.core.llm import fast_llm, invoke_llm
from app.agents.state import FinancialState

_HEALTH_PROMPT = """You are a financial health assessor for Indian users.
Given these 6 health dimension scores, provide the top 3 specific actions to improve the weakest areas.

Scores:
{scores}

Overall: {grade} ({overall}/100)

Be specific with ₹ amounts and actionable steps. Prioritise the lowest-scoring dimensions."""


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
        }
    emergency = profile.get("emergency_fund", 0)
    life_cover = profile.get("life_insurance_cover", 0)
    has_health = profile.get("has_health_insurance", False)
    monthly_emi = profile.get("monthly_emi", 0)
    investments_80c = profile.get("investments_80c", 0)
    fire_target = profile.get("fire_corpus_target", 0)
    age = profile.get("age", 30)

    funds = (portfolio.get("funds") or []) if portfolio else []
    portfolio_value = portfolio.get("current_value", 0) if portfolio else 0

    scores = {}

    # 1. Emergency Preparedness (20%) — target: 6 months expenses
    target_emergency = expenses * 6
    if target_emergency > 0:
        scores["emergency_preparedness"] = {
            "score": min(round(emergency / target_emergency * 100), 100),
            "weight": 20,
            "detail": f"₹{emergency:,.0f} of ₹{target_emergency:,.0f} target (6 months)",
        }
    else:
        scores["emergency_preparedness"] = {"score": 50, "weight": 20, "detail": "No expense data"}

    # 2. Insurance Coverage (20%) — term: 15-20x income, health: required
    annual_income = income * 12
    recommended_life = annual_income * 15
    life_score = min(round(life_cover / recommended_life * 100), 100) if recommended_life > 0 else 0
    health_score = 100 if has_health else 0
    scores["insurance_coverage"] = {
        "score": round((life_score * 0.6 + health_score * 0.4)),
        "weight": 20,
        "detail": f"Life: ₹{life_cover:,.0f}/₹{recommended_life:,.0f}, Health: {'Yes' if has_health else 'No'}",
    }

    # 3. Investment Diversification (15%)
    categories = set(f.get("category", "unknown") for f in funds) if funds else set()
    div_score = min(len(categories) * 25, 100)
    scores["investment_diversification"] = {
        "score": div_score,
        "weight": 15,
        "detail": f"{len(categories)} categories across {len(funds)} funds",
    }

    # 4. Debt Health (20%) — EMI to income ratio < 35%
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

    # 5. Tax Efficiency (10%) — 80C utilisation
    tax_score = min(round(investments_80c / 150000 * 100), 100) if investments_80c > 0 else 0
    scores["tax_efficiency"] = {
        "score": tax_score,
        "weight": 10,
        "detail": f"80C: ₹{investments_80c:,.0f}/₹1,50,000",
    }

    # 6. Retirement Readiness (15%)
    if fire_target > 0 and portfolio_value > 0:
        ret_score = min(round(portfolio_value / fire_target * 100), 100)
    else:
        # Estimate: should have ~1x annual income saved per decade of age
        target_by_age = annual_income * max((age - 20) / 10, 0.5)
        total_savings = portfolio_value + profile.get("epf_balance", 0) + profile.get("ppf_balance", 0)
        ret_score = min(round(total_savings / target_by_age * 100), 100) if target_by_age > 0 else 50
    scores["retirement_readiness"] = {
        "score": ret_score,
        "weight": 15,
        "detail": f"Portfolio: ₹{portfolio_value:,.0f}",
    }

    # Overall weighted score
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

    # Benchmark comparison — Social Proof (age-band + city averages)
    age_band = f"{(age // 5) * 5}-{(age // 5) * 5 + 4}"
    city = profile.get("city", "").strip().lower()
    # Approximate peer benchmarks by age band (based on aggregated Indian financial data)
    _BENCHMARKS = {
        "25-29": {"avg_score": 42, "emergency_pct": 35, "insurance_pct": 25, "sip_pct": 45},
        "30-34": {"avg_score": 48, "emergency_pct": 45, "insurance_pct": 40, "sip_pct": 55},
        "35-39": {"avg_score": 54, "emergency_pct": 55, "insurance_pct": 55, "sip_pct": 62},
        "40-44": {"avg_score": 58, "emergency_pct": 60, "insurance_pct": 65, "sip_pct": 68},
        "45-49": {"avg_score": 55, "emergency_pct": 58, "insurance_pct": 70, "sip_pct": 60},
    }
    # Metro city adjustments
    _METRO_BONUS = {"bengaluru": 3, "bangalore": 3, "mumbai": 2, "delhi": 1,
                     "hyderabad": 2, "pune": 2, "chennai": 1, "kolkata": 0}
    bench = _BENCHMARKS.get(age_band, {"avg_score": 50, "emergency_pct": 45, "insurance_pct": 45, "sip_pct": 50})
    peer_avg = bench["avg_score"] + _METRO_BONUS.get(city, 0)
    score_vs_peers = overall - peer_avg
    benchmark = {
        "age_band": age_band,
        "city": city or "India",
        "peer_avg_score": peer_avg,
        "your_score": overall,
        "diff": score_vs_peers,
        "percentile": min(max(round(50 + score_vs_peers * 2), 5), 95),
        "peer_emergency_pct": bench["emergency_pct"],
        "peer_insurance_pct": bench["insurance_pct"],
        "peer_sip_pct": bench["sip_pct"],
        "insight": f"Your score of {overall} is {'above' if score_vs_peers > 0 else 'below'} the average of {peer_avg} for {age_band} year olds in {city.title() or 'India'}.",
    }

    # LLM top 3 actions
    try:
        result = await invoke_llm(
            fast_llm,
            _HEALTH_PROMPT.format(scores=str(scores), grade=grade, overall=overall),
        )
        actions = result.content.strip()
    except Exception:
        actions = ""

    return {
        "overall_score": overall,
        "grade": grade,
        "dimensions": scores,
        "benchmark": benchmark,
        "top_actions": actions,
    }


async def run_money_health(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "health score", "intent": "money_health",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "money_health", "health score", language, voice_mode)
    return {"analysis": output, "response": response}
