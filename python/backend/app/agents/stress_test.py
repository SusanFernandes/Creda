"""
Stress Test agent — NumPy Monte Carlo with optional user stress scenarios from assumptions.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from app.agents.state import FinancialState
from app.core.agent_envelope import wrap_agent_response
from app.core.llm import primary_llm
from app.database import AsyncSessionLocal

_MITIGATION_PROMPT = """Given these stress test results for an Indian investor, provide 3 specific mitigation strategies.

Profile: Income ₹{income}/month, Expenses ₹{expenses}/month, Emergency fund ₹{emergency}, Portfolio ₹{portfolio}
Results: {results}

Provide 3 numbered, actionable strategies. Be specific with numbers."""

ITERATIONS = 1000


def run_monte_carlo(
    current_corpus: float,
    monthly_sip: float,
    years_to_retire: int,
    blended_return: float,
    _inflation_rate: float,
    stress_events: list[dict[str, Any]],
    *,
    goal_corpus: float,
    iterations: int = ITERATIONS,
) -> dict[str, Any]:
    months = max(int(years_to_retire * 12), 1)
    monthly_mean = blended_return / 12
    monthly_std = 0.18 / np.sqrt(12)

    rng = np.random.default_rng()
    returns = rng.normal(monthly_mean, monthly_std, (iterations, months))

    sip_matrix = np.full((iterations, months), float(monthly_sip))
    for event in stress_events:
        if not event.get("active"):
            continue
        start = int(event.get("start_month", 0))
        dur = int(event.get("duration_months", 6))
        cost = float(event.get("monthly_cost", 0))
        end = min(start + dur, months)
        sip_matrix[:, start:end] -= cost

    corpus = np.full(iterations, float(current_corpus))
    for m in range(months):
        corpus = corpus * (1.0 + returns[:, m]) + sip_matrix[:, m]
        corpus = np.maximum(corpus, 0.0)

    final = corpus
    survival = float(np.mean(final >= goal_corpus) * 100)
    return {
        "p10": float(np.percentile(final, 10)),
        "p50": float(np.percentile(final, 50)),
        "p90": float(np.percentile(final, 90)),
        "survival_probability_pct": survival,
        "iterations": iterations,
        "final_samples": final,
    }


async def run(state: FinancialState) -> dict[str, Any]:
    from app.agents.profile_checks import require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    income = float(profile["monthly_income"])
    expenses = float(profile["monthly_expenses"])
    emergency = float(profile.get("emergency_fund") or 0)
    portfolio_value = float(portfolio.get("current_value") or 0)
    age = int(profile["age"])
    fire_age = int(profile["fire_target_age"])

    async with AsyncSessionLocal() as db:
        from app.core.assumptions import get_user_assumptions

        assumptions = await get_user_assumptions(db, state["user_id"])

    blended = float(assumptions["equity_lc_return"])
    inflation_rate = float(assumptions["inflation_rate"])
    monthly_sip = max(income - expenses, 0)

    years_to_retire = max(fire_age - age, 5)
    annual_exp = expenses * 12
    goal_corpus = max(annual_exp * 25, portfolio_value * 1.2)

    raw_scenarios = assumptions.get("stress_scenarios") or {}
    stress_events: list[dict[str, Any]] = []
    if isinstance(raw_scenarios, dict):
        for key, cfg in raw_scenarios.items():
            if isinstance(cfg, dict):
                stress_events.append({"name": key, **cfg})

    if not stress_events:
        stress_events = [
            {"active": True, "start_month": 0, "duration_months": 6, "monthly_cost": expenses * 0.9},
        ]

    mc = run_monte_carlo(
        portfolio_value + emergency * 0.5,
        monthly_sip,
        years_to_retire,
        blended,
        inflation_rate,
        stress_events,
        goal_corpus=goal_corpus,
    )

    inner = {
        "p10_corpus": mc["p10"],
        "p50_corpus": mc["p50"],
        "p90_corpus": mc["p90"],
        "survival_probability_pct": mc["survival_probability_pct"],
        "retire_date_shift_months": {},
        "emergency_fund_required": round(expenses * 6),
        "emergency_fund_current": round(emergency),
        "emergency_fund_gap": round(max(expenses * 6 - emergency, 0)),
        "iterations": mc["iterations"],
    }

    try:
        prompt = _MITIGATION_PROMPT.format(
            income=income,
            expenses=expenses,
            emergency=emergency,
            portfolio=portfolio_value,
            results=str(inner),
        )
        llm_result = await primary_llm.ainvoke(prompt)
        mitigation = llm_result.content.strip()
    except Exception:
        mitigation = ""

    inner["mitigation_strategies"] = mitigation

    out = wrap_agent_response(
        "stress_test",
        "success",
        "estimated",
        {"inflation_rate": inflation_rate, "equity_return": blended},
        inner,
    )
    out["data_quality"] = "estimated"
    return out


async def run_stress_test(profile, events: list[str], language: str, voice_mode: bool) -> dict:
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
    inner = output.get("output", output) if isinstance(output, dict) else output
    response = await synthesize(inner, "stress_test", state["message"], language, voice_mode)
    return {"analysis": inner, "response": response}
