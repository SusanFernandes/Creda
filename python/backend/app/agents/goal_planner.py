"""
Goal Planner agent — target-based savings plans (house, car, education, wedding, etc.).
"""
import math
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_GOAL_PROMPT = """You are a financial goal planner for Indian users. Given these goal calculations, provide:
1. Whether the goals are realistic given their income
2. Priority order if they can't fund all goals simultaneously
3. One suggestion to accelerate the most important goal

Data:
{data}

Be practical and specific with ₹ amounts and timelines."""


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    message = state.get("message", "")

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    available_sip = income - expenses

    # Parse goal from message or use common Indian goals
    goals = _extract_goals(message, income)

    for goal in goals:
        target = goal["target_amount"]
        years = goal["years"]
        annual_return = 0.12 if years > 5 else 0.08  # equity vs debt
        monthly_return = annual_return / 12
        months = years * 12

        if monthly_return > 0 and months > 0:
            required_sip = target * monthly_return / (((1 + monthly_return) ** months) - 1)
        else:
            required_sip = target / max(months, 1)

        # Progress tracking
        current_saved = goal.get("current_saved", 0)
        progress_pct = round(current_saved / target * 100, 1) if target > 0 else 0
        expected_at_this_point = target * (1 - (months - (years * 12 - months)) / months) if months > 0 else 0

        # Drift calculation
        drift = current_saved - expected_at_this_point
        is_on_track = drift >= 0

        # If SIP increase could fix it
        sip_increase_needed = 0
        if not is_on_track and months > 0:
            remaining_target = target - current_saved
            if monthly_return > 0:
                sip_increase_needed = remaining_target * monthly_return / (((1 + monthly_return) ** months) - 1) - required_sip
            sip_increase_needed = max(round(sip_increase_needed), 0)

        goal["required_sip"] = round(required_sip)
        goal["annual_return"] = annual_return * 100
        goal["affordable"] = required_sip <= available_sip
        goal["pct_of_savings"] = round(required_sip / available_sip * 100, 1) if available_sip > 0 else 0
        goal["progress_pct"] = progress_pct
        goal["current_saved"] = current_saved
        goal["drift"] = round(drift)
        goal["is_on_track"] = is_on_track
        goal["sip_increase_needed"] = sip_increase_needed

    total_sip_needed = sum(g["required_sip"] for g in goals)
    underfunded_goals = [g for g in goals if not g.get("is_on_track", True)]

    data = {
        "available_monthly_sip": available_sip,
        "total_sip_needed": total_sip_needed,
        "affordable": total_sip_needed <= available_sip,
        "goals": goals,
        "drift_alerts": [
            {
                "goal": g["name"],
                "shortfall": abs(g.get("drift", 0)),
                "sip_increase_needed": g.get("sip_increase_needed", 0),
                "message": f"{g['name']} is underfunded by ₹{abs(g.get('drift', 0)):,.0f}. Increase SIP by ₹{g.get('sip_increase_needed', 0):,.0f}/month.",
            }
            for g in underfunded_goals
        ],
    }

    try:
        result = await primary_llm.ainvoke(_GOAL_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_goal_planner(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "goal planning", "intent": "goal_planner",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "goal_planner", "goal planning", language, voice_mode)
    return {"analysis": output, "response": response}


def _extract_goals(message: str, income: float) -> list[dict]:
    """Extract goals from message or provide common defaults."""
    msg = message.lower()
    goals = []

    if "house" in msg or "home" in msg:
        goals.append({"name": "House Down Payment", "target_amount": income * 12 * 5, "years": 5})
    if "car" in msg:
        goals.append({"name": "Car", "target_amount": income * 12, "years": 3})
    if "education" in msg or "child" in msg:
        goals.append({"name": "Child Education", "target_amount": 2_000_000, "years": 15})
    if "wedding" in msg or "marriage" in msg:
        goals.append({"name": "Wedding", "target_amount": 1_500_000, "years": 3})
    if "vacation" in msg or "travel" in msg:
        goals.append({"name": "Vacation", "target_amount": 200_000, "years": 1})

    if not goals:
        # Default common goals
        goals = [
            {"name": "Emergency Fund (6 months)", "target_amount": income * 6, "years": 2},
            {"name": "House Down Payment", "target_amount": income * 12 * 5, "years": 7},
            {"name": "Retirement Corpus", "target_amount": income * 12 * 25, "years": 25},
        ]

    return goals
