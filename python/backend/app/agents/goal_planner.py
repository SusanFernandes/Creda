"""
Goal Planner agent — target-based savings plans (house, car, education, wedding, etc.).
"""
from datetime import date
from typing import Any

from app.core.llm import invoke_llm, primary_llm
from app.agents.state import FinancialState

_GOAL_PROMPT = """You are a financial goal planner for Indian users. Given these goal calculations, provide:
1. Whether the goals are realistic given their income
2. Priority order if they can't fund all goals simultaneously
3. One suggestion to accelerate the most important goal

Data:
{data}

Be practical and specific with ₹ amounts and timelines."""


def _years_from_target_date(target_date) -> float:
    if not target_date:
        return 5.0
    if isinstance(target_date, str):
        try:
            td = date.fromisoformat(target_date[:10])
        except ValueError:
            return 5.0
    else:
        td = target_date
    years = (td - date.today()).days / 365.25
    return max(0.5, min(years, 40.0))


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    message = state.get("message", "")

    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    if income <= 0 or expenses <= 0:
        from app.services.profile_completeness import humanize_missing, missing_for_core_planning
        miss = missing_for_core_planning(profile)
        return {
            "input_required": True,
            "missing_fields_detail": humanize_missing(miss),
            "message": "Goal Planner needs monthly income and expenses from Settings to know what SIP you can afford.",
            "available_monthly_sip": 0,
            "total_sip_needed": 0,
            "affordable": False,
            "goals": [],
            "drift_alerts": [],
        }

    available_sip = income - expenses

    stored = state.get("stored_goals") or []
    if stored:
        goals = []
        for row in stored:
            tgt = float(row.get("target_amount") or 0)
            if tgt <= 0:
                continue
            years = _years_from_target_date(row.get("target_date"))
            goals.append({
                "name": row.get("goal_name") or "Goal",
                "target_amount": tgt,
                "years": years,
                "current_saved": float(row.get("current_saved") or 0),
            })
    else:
        goals = _extract_goals(message, income)

    if not goals:
        return {
            "input_required": False,
            "needs_goals": True,
            "message": "You have no goals saved yet. Add a goal below (or in the API), then reload — we will size SIPs from your real targets instead of generic examples.",
            "available_monthly_sip": available_sip,
            "total_sip_needed": 0,
            "affordable": True,
            "goals": [],
            "drift_alerts": [],
        }

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
        result = await invoke_llm(primary_llm, _GOAL_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_goal_planner(
    profile, language: str, voice_mode: bool, stored_goals: list[dict] | None = None,
) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "goal planning", "intent": "goal_planner",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
        "stored_goals": stored_goals or [],
    }
    output = await run(state)
    response = await synthesize(output, "goal_planner", "goal planning", language, voice_mode)
    return {"analysis": output, "response": response}


def _extract_goals(message: str, income: float) -> list[dict]:
    """Extract goals from chat-style message only — no silent defaults."""
    msg = message.lower()
    goals: list[dict] = []

    if "house" in msg or "home" in msg:
        goals.append({"name": "House Down Payment", "target_amount": income * 12 * 5, "years": 5, "current_saved": 0})
    if "car" in msg:
        goals.append({"name": "Car", "target_amount": income * 12, "years": 3, "current_saved": 0})
    if "education" in msg or "child" in msg:
        goals.append({"name": "Child Education", "target_amount": 2_000_000, "years": 15, "current_saved": 0})
    if "wedding" in msg or "marriage" in msg:
        goals.append({"name": "Wedding", "target_amount": 1_500_000, "years": 3, "current_saved": 0})
    if "vacation" in msg or "travel" in msg:
        goals.append({"name": "Vacation", "target_amount": 200_000, "years": 1, "current_saved": 0})

    return goals
