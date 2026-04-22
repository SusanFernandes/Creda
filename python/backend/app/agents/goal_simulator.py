"""
Goal Simulator agent — visual "what-if" scenario modeling for financial goals.
Drag-slider scenarios: "What if I increase SIP by ₹2,000?" / "What if returns are 8% instead of 12?"
"""
import math
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_SIMULATOR_PROMPT = """You are a goal simulation expert. Given the user's goal scenarios below, provide:
1. Which scenario is most realistic and why
2. One specific action to improve the base case
3. Warning if any scenario assumes unrealistic returns

Data: {data}
Respond concisely. Use ₹ amounts."""


def _sip_future_value(monthly: float, annual_return: float, years: int) -> float:
    """Calculate future value of monthly SIP."""
    r = annual_return / 12
    n = years * 12
    if r <= 0:
        return monthly * n
    return monthly * (((1 + r) ** n - 1) / r) * (1 + r)


def _required_sip(target: float, annual_return: float, years: int) -> float:
    """Calculate required monthly SIP to reach target."""
    r = annual_return / 12
    n = years * 12
    if r <= 0:
        return target / n if n > 0 else 0
    return target / ((((1 + r) ** n - 1) / r) * (1 + r))


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    message = state.get("message", "")

    # Extract scenario parameters from message or use defaults
    current_sip = profile.get("monthly_income", 50000) - profile.get("monthly_expenses", 30000)
    current_sip = max(current_sip, 5000)

    # Parse goal details
    goal_name = "Financial Goal"
    target_amount = 5000000  # ₹50 lakh default
    years = 10
    base_return = 0.12  # 12% nominal

    import re
    target_match = re.search(r"(\d+[\d,]*)\s*(?:lakh|lac)", message, re.I)
    if target_match:
        target_amount = float(target_match.group(1).replace(",", "")) * 100000
    crore_match = re.search(r"(\d+\.?\d*)\s*(?:crore|cr)", message, re.I)
    if crore_match:
        target_amount = float(crore_match.group(1)) * 10000000

    years_match = re.search(r"(\d+)\s*years?", message, re.I)
    if years_match:
        years = int(years_match.group(1))

    # Generate 5 scenarios
    scenarios = []
    adjustments = [
        ("Base Case", 0, base_return),
        ("+₹2,000/month SIP", 2000, base_return),
        ("+₹5,000/month SIP", 5000, base_return),
        ("Conservative (8% return)", 0, 0.08),
        ("Aggressive (15% return)", 0, 0.15),
    ]

    for label, sip_delta, ret in adjustments:
        sip = current_sip + sip_delta
        fv = _sip_future_value(sip, ret, years)
        shortfall = max(target_amount - fv, 0)
        on_track = fv >= target_amount

        # Year-by-year projection
        yearly = []
        for y in range(1, years + 1):
            yearly.append({
                "year": y,
                "value": round(_sip_future_value(sip, ret, y)),
            })

        scenarios.append({
            "label": label,
            "monthly_sip": round(sip),
            "annual_return": round(ret * 100, 1),
            "projected_value": round(fv),
            "target": round(target_amount),
            "shortfall": round(shortfall),
            "on_track": on_track,
            "completion_pct": min(round(fv / target_amount * 100, 1), 100) if target_amount > 0 else 0,
            "yearly_projection": yearly,
        })

    required = _required_sip(target_amount, base_return, years)

    data = {
        "goal_name": goal_name,
        "target_amount": round(target_amount),
        "years": years,
        "current_sip": round(current_sip),
        "required_sip": round(required),
        "sip_gap": round(max(required - current_sip, 0)),
        "scenarios": scenarios,
    }

    try:
        result = await primary_llm.ainvoke(_SIMULATOR_PROMPT.format(data=str({
            "scenarios": [{"label": s["label"], "projected": s["projected_value"],
                          "target": s["target"], "on_track": s["on_track"]} for s in scenarios],
            "required_sip": round(required),
            "current_sip": round(current_sip),
        })))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_goal_simulator(profile, language: str, voice_mode: bool,
                              target_amount: float = 5000000, years: int = 10) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": f"goal simulator target {target_amount} in {years} years",
        "intent": "goal_simulator",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "goal_simulator", "goal simulation", language, voice_mode)
    return {"analysis": output, "response": response}
