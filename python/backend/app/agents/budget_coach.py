"""
Budget Coach agent — spending analysis, 50/30/20 rule, category breakdown, savings rate.
"""
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_BUDGET_PROMPT = """You are a budget coach for Indian users. Given this spending analysis, provide:
1. How they compare to the 50/30/20 rule
2. Top 2 areas where they can cut spending
3. A realistic monthly savings target

Data:
{data}

Be specific with ₹ amounts. Keep it encouraging, not judgmental."""


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    emi = profile.get("monthly_emi", 0)
    savings = income - expenses

    # 50/30/20 rule analysis
    needs_target = income * 0.50
    wants_target = income * 0.30
    savings_target = income * 0.20

    # Approximate breakdown (needs = expenses - emi, wants = emi area, savings = remainder)
    actual_needs = expenses - emi
    actual_wants = emi  # simplified — EMIs are fixed obligations
    actual_savings = savings

    savings_rate = (savings / income * 100) if income > 0 else 0

    data = {
        "monthly_income": income,
        "monthly_expenses": expenses,
        "monthly_savings": savings,
        "savings_rate": round(savings_rate, 1),
        "rule_50_30_20": {
            "needs": {"target": needs_target, "actual": actual_needs,
                       "status": "ok" if actual_needs <= needs_target else "over"},
            "wants": {"target": wants_target, "actual": actual_wants,
                       "status": "ok" if actual_wants <= wants_target else "over"},
            "savings": {"target": savings_target, "actual": actual_savings,
                         "status": "ok" if actual_savings >= savings_target else "under"},
        },
        "emi_to_income": round(emi / income * 100, 1) if income > 0 else 0,
        "emergency_fund": profile.get("emergency_fund", 0),
        "months_of_runway": round(profile.get("emergency_fund", 0) / expenses, 1) if expenses > 0 else 0,
    }

    try:
        result = await primary_llm.ainvoke(_BUDGET_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_budget_coach(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "budget analysis", "intent": "budget_coach",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "budget_coach", "budget analysis", language, voice_mode)
    return {"analysis": output, "response": response}
