"""
Stress Test agent — Monte Carlo with NumPy RNG and batched month updates (vectorised over paths).
Optional stress_scenario_params + UserAssumptions.stress_scenarios.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_DEFAULT_EVENTS = {
    "market_crash_30": {"label": "Market crash 30%", "portfolio_hit": -0.30, "monthly_cost": 0},
    "market_crash_50": {"label": "Market crash 50%", "portfolio_hit": -0.50, "monthly_cost": 0},
    "baby": {"label": "Having a baby", "portfolio_hit": 0, "monthly_cost": 25000},
    "marriage": {"label": "Marriage", "portfolio_hit": 0, "monthly_cost": 15000},
    "job_loss": {"label": "Job loss", "portfolio_hit": 0, "monthly_cost": 0, "income_hit_months": 6},
    "job_change": {"label": "Job change (+30% salary)", "portfolio_hit": 0, "monthly_cost": -0.30},
    "retirement": {"label": "Early retirement", "portfolio_hit": 0, "monthly_cost": 0},
    "medical_emergency": {"label": "Medical emergency", "portfolio_hit": -0.05, "monthly_cost": 0, "one_time_hit": 500000},
    "parent_support": {"label": "Parent support", "portfolio_hit": 0, "monthly_cost": 15000},
}

_MITIGATION_PROMPT = """Given these stress test results for an Indian investor, provide 3 specific mitigation strategies.

Profile: Income ₹{income}/month, Expenses ₹{expenses}/month, Emergency fund ₹{emergency}, Portfolio ₹{portfolio}
Events tested: {events}
Results: {results}

Provide 3 numbered, actionable strategies. Be specific with numbers."""

ITERATIONS = 1000


def _event_with_params(base: dict, params: dict[str, Any], event_key: str) -> dict[str, Any]:
    ev = dict(base)
    sc = params or {}
    if event_key == "baby":
        ev["monthly_cost"] = float(sc.get("baby_monthly_cost", ev.get("monthly_cost", 25000)))
    if event_key == "job_loss":
        m = int(sc.get("job_loss_months", ev.get("income_hit_months", 6)))
        ev["income_hit_months"] = m
        ev["label"] = f"Job loss ({m} months)"
    if event_key == "medical_emergency":
        ev["one_time_hit"] = float(sc.get("medical_emergency_cost", ev.get("one_time_hit", 500000)))
    if event_key == "parent_support":
        ev["monthly_cost"] = float(sc.get("parent_support_monthly", ev["monthly_cost"]))
    return ev


def _simulate_paths(
    portfolio: float,
    income: float,
    expenses: float,
    emergency: float,
    event: dict[str, Any],
    iterations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return final wealth (portfolio + emergency) per path after 12 months."""
    months = 12
    p = np.full(iterations, portfolio, dtype=np.float64)
    e = np.full(iterations, emergency, dtype=np.float64)

    port_hit = float(event.get("portfolio_hit", 0))
    p *= 1.0 + port_hit + rng.normal(0, 0.05, size=iterations)
    p = np.maximum(p, 0.0)

    one_time = float(event.get("one_time_hit", 0))
    if one_time > 0:
        p -= one_time * rng.uniform(0.85, 1.0, size=iterations)
        p = np.maximum(p, 0.0)

    extra_cost = float(event.get("monthly_cost", 0) or 0)
    income_hit_months = int(event.get("income_hit_months", 0))
    monthly_savings = income - expenses

    if isinstance(extra_cost, float) and -1 < extra_cost < 0:
        monthly_savings = monthly_savings * (1.0 - extra_cost)
        extra_cost = 0.0

    monthly_ret = rng.normal(0.01, 0.04, size=(iterations, months))

    for month in range(months):
        p *= 1.0 + monthly_ret[:, month]
        if month < income_hit_months:
            net_scalar = -expenses - extra_cost
        else:
            net_scalar = monthly_savings - extra_cost
        netv = np.full(iterations, net_scalar, dtype=np.float64)
        neg = netv < 0
        pos = ~neg
        if np.any(neg):
            e[neg] = e[neg] + netv[neg]
            spill = np.minimum(e[neg], 0.0)
            p[neg] = p[neg] + spill
            e[neg] = np.maximum(e[neg], 0.0)
        if np.any(pos):
            p[pos] = p[pos] + netv[pos] * 0.5
            e[pos] = e[pos] + netv[pos] * 0.5

    return p + e


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}
    message = state.get("message", "")
    params: dict[str, Any] = dict(state.get("stress_scenario_params") or {})
    if not params and state.get("user_id"):
        try:
            from app.database import AsyncSessionLocal
            from app.core.assumptions import get_user_assumptions

            async with AsyncSessionLocal() as db:
                assumptions = await get_user_assumptions(db, state["user_id"])
                params = dict(assumptions.get("stress_scenarios") or {})
        except Exception:
            params = {}

    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    if income <= 0 or expenses <= 0:
        return {
            "input_required": True,
            "profile_message": "Add monthly income and expenses in Settings to simulate realistic stress outcomes.",
            "events_tested": [],
            "results": {},
            "mitigation_strategies": "",
        }

    emergency = float(profile.get("emergency_fund") or 0)
    portfolio_value = float(portfolio.get("current_value", 0) or 0)
    fire_target = float(profile.get("fire_corpus_target") or 0) or (expenses * 12 * 25)

    explicit = state.get("stress_event_keys") or []
    events_to_test = [e for e in explicit if e in _DEFAULT_EVENTS]
    if not events_to_test:
        events_to_test = _detect_events(message)
    if not events_to_test:
        events_to_test = ["market_crash_30", "baby", "job_loss"]

    rng = np.random.default_rng()
    baseline_event = {"portfolio_hit": 0, "monthly_cost": 0, "income_hit_months": 0, "one_time_hit": 0}
    baseline_paths = _simulate_paths(
        portfolio_value, income, expenses, emergency, baseline_event, ITERATIONS, rng,
    )
    baseline_med = float(np.median(baseline_paths))
    floor = expenses * 6
    survival_baseline = float(np.mean(baseline_paths > floor))

    results: dict[str, Any] = {}
    for event_key in events_to_test:
        base = _DEFAULT_EVENTS.get(event_key)
        if not base:
            continue
        event = _event_with_params(base, params, event_key)
        rng = np.random.default_rng()
        scenarios = _simulate_paths(
            portfolio_value, income, expenses, emergency, event, ITERATIONS, rng,
        )
        scenarios.sort()
        p50 = float(scenarios[int(ITERATIONS * 0.5)])
        survival = float(np.mean(scenarios > floor))
        ret_delay_months = 0
        if fire_target > 0 and p50 < fire_target * 0.95:
            shortfall = max(fire_target - p50, 0)
            monthly_surplus = max(income - expenses, 1)
            ret_delay_months = int(min(120, shortfall / monthly_surplus))

        results[event_key] = {
            "label": event["label"],
            "p10": round(float(scenarios[int(ITERATIONS * 0.1)])),
            "p50": round(p50),
            "p90": round(float(scenarios[int(ITERATIONS * 0.9)])),
            "worst_case": round(float(scenarios[0])),
            "best_case": round(float(scenarios[-1])),
            "survival_probability_pct": round(survival * 100, 1),
            "baseline_survival_probability_pct": round(survival_baseline * 100, 1),
            "emergency_fund_months_target": 6,
            "emergency_fund_gap": round(max(floor - emergency, 0)),
            "estimated_retirement_delay_months": ret_delay_months,
            "median_vs_baseline_no_stress": round(p50 - baseline_med),
        }

    try:
        prompt = _MITIGATION_PROMPT.format(
            income=income,
            expenses=expenses,
            emergency=emergency,
            portfolio=portfolio_value,
            events=events_to_test,
            results=str(results),
        )
        llm_result = await primary_llm.ainvoke(prompt)
        mitigation = llm_result.content.strip()
    except Exception:
        mitigation = ""

    if not mitigation and results:
        lines = [
            "Mitigation (automated):",
            "1. Keep 6+ months of expenses in a liquid fund before adding risk.",
            "2. If survival probability drops under 70%, increase emergency fund or reduce discretionary spend.",
            "3. Maintain term + health insurance so a shock does not force equity redemptions at the bottom.",
        ]
        for ek, r in results.items():
            lines.append(
                f"- {r['label']}: median ~₹{r['p50']:,}; survival ~{r.get('survival_probability_pct', 0)}%."
            )
        mitigation = "\n".join(lines)

    return {
        "events_tested": events_to_test,
        "results": results,
        "mitigation_strategies": mitigation,
        "monte_carlo_engine": "numpy_batched_paths",
        "iterations": ITERATIONS,
    }


async def run_stress_test(
    profile,
    events: list[str],
    language: str,
    voice_mode: bool,
    stress_scenario_params: dict | None = None,
) -> dict:
    from app.agents.synthesizer import synthesize

    state: FinancialState = {
        "user_id": profile.user_id,
        "message": f"stress test for {', '.join(events)}",
        "intent": "stress_test",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns},
        "stress_event_keys": events,
        "stress_scenario_params": stress_scenario_params,
    }
    output = await run(state)
    response = await synthesize(output, "stress_test", state["message"], language, voice_mode)
    return {"analysis": output, "response": response}


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
    if "medical" in msg or "hospital" in msg:
        detected.append("medical_emergency")
    if "parent" in msg and ("support" in msg or "dependent" in msg):
        detected.append("parent_support")
    return detected
