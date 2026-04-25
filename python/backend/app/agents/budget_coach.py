"""
Budget Coach agent — spending analysis, 50/30/20 rule, category breakdown, savings rate.
"""
from typing import Any

from app.core.llm import fast_llm, invoke_llm
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

    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    if income <= 0 or expenses <= 0:
        from app.services.profile_completeness import humanize_missing, missing_for_core_planning
        miss = missing_for_core_planning(profile)
        return {
            "input_required": True,
            "missing_fields_detail": humanize_missing(miss),
            "message": "Budget Coach needs your actual monthly income and expenses from Settings (no default assumptions).",
        }

    emi = float(profile.get("monthly_emi") or 0)
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
        result = await invoke_llm(fast_llm, _BUDGET_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    if not data.get("advice"):
        r = data["rule_50_30_20"]
        data["advice"] = (
            f"50/30/20 snapshot: needs target ₹{r['needs']['target']:,.0f} (actual ₹{r['needs']['actual']:,.0f}, "
            f"{r['needs']['status']}). Wants target ₹{r['wants']['target']:,.0f}. "
            f"Savings target ₹{r['savings']['target']:,.0f} vs actual ₹{r['savings']['actual']:,.0f}. "
            f"Next step: move at least ₹{max(0, r['savings']['target'] - r['savings']['actual']):,.0f}/mo into SIP or emergency fund auto-debit."
        )

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
