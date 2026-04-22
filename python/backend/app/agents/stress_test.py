"""
Stress Test agent — Monte Carlo simulations for life events.
500 iterations per event, P10/P50/P90 outcomes.
"""
import random
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_EVENTS = {
    "market_crash_30": {"label": "Market crash 30%", "portfolio_hit": -0.30, "monthly_cost": 0},
    "market_crash_50": {"label": "Market crash 50%", "portfolio_hit": -0.50, "monthly_cost": 0},
    "baby": {"label": "Having a baby", "portfolio_hit": 0, "monthly_cost": 25000},
    "marriage": {"label": "Marriage", "portfolio_hit": 0, "monthly_cost": 15000},
    "job_loss": {"label": "Job loss (6 months)", "portfolio_hit": 0, "monthly_cost": 0, "income_hit_months": 6},
    "job_change": {"label": "Job change (+30% salary)", "portfolio_hit": 0, "monthly_cost": -0.30},
    "retirement": {"label": "Early retirement", "portfolio_hit": 0, "monthly_cost": 0},
}

_MITIGATION_PROMPT = """Given these stress test results for an Indian investor, provide 3 specific mitigation strategies.

Profile: Income ₹{income}/month, Expenses ₹{expenses}/month, Emergency fund ₹{emergency}, Portfolio ₹{portfolio}
Events tested: {events}
Results: {results}

Provide 3 numbered, actionable strategies. Be specific with numbers."""

ITERATIONS = 500


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}
    message = state.get("message", "")

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    savings_rate = (income - expenses) / income if income > 0 else 0.2
    emergency = profile.get("emergency_fund", 0)
    portfolio_value = portfolio.get("current_value", 0) or 0

    # Detect which events to test from message
    events_to_test = _detect_events(message)
    if not events_to_test:
        events_to_test = ["market_crash_30", "baby", "job_loss"]

    results = {}
    for event_key in events_to_test:
        event = _EVENTS.get(event_key)
        if not event:
            continue
        scenarios = _monte_carlo(
            portfolio_value, income, expenses, emergency, savings_rate, event
        )
        scenarios.sort()
        results[event_key] = {
            "label": event["label"],
            "p10": round(scenarios[int(ITERATIONS * 0.1)]),
            "p50": round(scenarios[int(ITERATIONS * 0.5)]),
            "p90": round(scenarios[int(ITERATIONS * 0.9)]),
            "worst_case": round(scenarios[0]),
            "best_case": round(scenarios[-1]),
        }

    # LLM mitigation strategies
    try:
        prompt = _MITIGATION_PROMPT.format(
            income=income, expenses=expenses, emergency=emergency,
            portfolio=portfolio_value, events=events_to_test, results=str(results),
        )
        llm_result = await primary_llm.ainvoke(prompt)
        mitigation = llm_result.content.strip()
    except Exception:
        mitigation = ""

    return {
        "events_tested": events_to_test,
        "results": results,
        "mitigation_strategies": mitigation,
    }


async def run_stress_test(profile, events: list[str], language: str, voice_mode: bool) -> dict:
    """Direct endpoint call — skip LangGraph."""
    from app.agents.synthesizer import synthesize
    state: FinancialState = {
        "user_id": profile.user_id,
        "message": f"stress test for {', '.join(events)}",
        "intent": "stress_test",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns},
    }
    output = await run(state)
    response = await synthesize(output, "stress_test", state["message"], language, voice_mode)
    return {"analysis": output, "response": response}


def _monte_carlo(portfolio: float, income: float, expenses: float,
                 emergency: float, savings_rate: float, event: dict) -> list[float]:
    results = []
    for _ in range(ITERATIONS):
        p = portfolio
        e = emergency
        monthly_savings = income - expenses

        # Apply portfolio hit
        p *= (1 + event.get("portfolio_hit", 0) + random.gauss(0, 0.05))

        # Apply monthly cost increase (12 months projection)
        extra_cost = event.get("monthly_cost", 0)
        if isinstance(extra_cost, float) and -1 < extra_cost < 0:
            # Negative = income increase (e.g., job_change)
            monthly_savings *= (1 - extra_cost)
            extra_cost = 0

        income_hit_months = event.get("income_hit_months", 0)

        for month in range(12):
            monthly_return = random.gauss(0.01, 0.04)  # ~12% annual, 16% vol
            p *= (1 + monthly_return)

            if month < income_hit_months:
                net = -expenses - extra_cost
            else:
                net = monthly_savings - extra_cost

            if net < 0:
                e += net
                if e < 0:
                    p += e
                    e = 0
            else:
                p += net * 0.5
                e += net * 0.5

        results.append(p + e)
    return results


def _detect_events(message: str) -> list[str]:
    msg = message.lower()
    detected = []
    if "crash" in msg and "50" in msg:
        detected.append("market_crash_50")
    elif "crash" in msg or "market" in msg:
        detected.append("market_crash_30")
    if "baby" in msg or "child" in msg:
        detected.append("baby")
    if "marriage" in msg or "wedding" in msg:
        detected.append("marriage")
    if "job loss" in msg or "fired" in msg or "layoff" in msg:
        detected.append("job_loss")
    if "job change" in msg or "new job" in msg:
        detected.append("job_change")
    if "retire" in msg:
        detected.append("retirement")
    return detected
