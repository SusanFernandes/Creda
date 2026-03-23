"""
Stress Test Agent — Monte Carlo simulation for life events.
Simulates portfolio impact of market crashes, babies, marriages, job changes, etc.
"""

from __future__ import annotations
import logging
from typing import Dict, Any
import numpy as np
from langchain_groq import ChatGroq
from agents.state import FinancialState

logger = logging.getLogger(__name__)

LIFE_EVENT_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "market_crash_30": {
        "label": "Market falls 30% for 18 months",
        "equity_hit": -0.30,
        "recovery_months": 24,
        "debt_impact": -0.02,
    },
    "market_crash_50": {
        "label": "Severe crash — markets fall 50%",
        "equity_hit": -0.50,
        "recovery_months": 48,
        "debt_impact": -0.03,
    },
    "baby": {
        "label": "New baby — expenses increase ₹25,000/month",
        "monthly_expense_increase": 25000,
        "duration_months": 36,
        "one_time_cost": 200000,
    },
    "home_purchase": {
        "label": "Home purchase — EMI impact",
        "monthly_expense_increase": 0,
        "down_payment_percent": 0.20,
        "loan_rate": 8.5,
        "loan_tenure_years": 20,
    },
    "job_change": {
        "label": "Job change — 3-month income gap",
        "income_gap_months": 3,
        "income_increase_after": 0.20,
    },
    "marriage": {
        "label": "Marriage — one-time cost + lifestyle change",
        "one_time_cost": 1000000,
        "monthly_expense_increase": 15000,
    },
    "bonus": {
        "label": "Bonus received — deployment strategy",
        "type": "positive",
    },
    "retirement": {
        "label": "Early retirement simulation",
        "type": "planning",
    },
}


def simulate_sip_under_stress(
    monthly_sip: float,
    current_corpus: float,
    event_type: str,
    user_profile: dict,
    years: int = 10,
    n_simulations: int = 500,
) -> dict:
    """Run *n_simulations* Monte-Carlo paths to show the range of outcomes."""
    scenario = LIFE_EVENT_SCENARIOS.get(event_type, {})
    months = years * 12
    results = []
    rng = np.random.default_rng(42)

    for _ in range(n_simulations):
        corpus = current_corpus
        sip = monthly_sip

        # ── Apply one-time costs ──
        corpus -= scenario.get("one_time_cost", 0)
        corpus = max(0, corpus)

        # ── Market crash scenarios ──
        if "equity_hit" in scenario:
            corpus *= (1 + scenario["equity_hit"])
            recovery = scenario.get("recovery_months", 24)
            for _ in range(min(recovery, months)):
                ret = rng.normal(0.003, 0.02)          # sluggish recovery
                corpus = corpus * (1 + ret) + sip

        # ── Expense increase ──
        if "monthly_expense_increase" in scenario:
            sip = max(0, sip - scenario["monthly_expense_increase"])

        # ── Income gap ──
        gap = scenario.get("income_gap_months", 0)
        start = gap if "equity_hit" not in scenario else 0

        for m in range(months):
            ret = rng.normal(0.01, 0.035)
            if m < start:
                corpus = corpus * (1 + ret)             # no SIP
            else:
                corpus = corpus * (1 + ret) + sip
        results.append(corpus)

    results.sort()

    # Baseline (no stress)
    baseline = current_corpus
    for _ in range(months):
        baseline = baseline * 1.01 + monthly_sip

    p10 = round(results[int(n_simulations * 0.10)], 0)
    p50 = round(results[int(n_simulations * 0.50)], 0)
    p90 = round(results[int(n_simulations * 0.90)], 0)

    return {
        "event": scenario.get("label", event_type),
        "baseline_corpus": round(baseline, 0),
        "stressed_p10": p10,
        "stressed_p50": p50,
        "stressed_p90": p90,
        "corpus_impact": round(p50 - baseline, 0),
        "corpus_impact_pct": round((p50 - baseline) / baseline * 100, 1) if baseline else 0,
        "retirement_date_shift_months": max(0, round((baseline - p50) / monthly_sip / 1.5)) if monthly_sip else 0,
        "simulation_count": n_simulations,
    }


def stress_test_agent(state: FinancialState) -> dict:
    """LangGraph node — life-event stress tester."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)
    user_profile = state.get("user_profile", {})
    portfolio = state.get("portfolio_data", {})
    last_message = state["messages"][-1].content

    # Detect event type via LLM
    event_prompt = (
        f'From this message, identify the financial life event.\n'
        f'Message: "{last_message}"\n'
        f'Choices: {", ".join(LIFE_EVENT_SCENARIOS.keys())}\n'
        f'Respond with ONLY the event key.'
    )
    try:
        event_key = llm.invoke(event_prompt).content.strip().lower()
        if event_key not in LIFE_EVENT_SCENARIOS:
            event_key = "market_crash_30"
    except Exception:
        event_key = "market_crash_30"

    monthly_sip = float(user_profile.get("monthly_sip", user_profile.get("income", 50000) * 0.2))
    current_corpus = float(portfolio.get("total_current_value", user_profile.get("savings", 100000)))

    simulation = simulate_sip_under_stress(
        monthly_sip=monthly_sip,
        current_corpus=current_corpus,
        event_type=event_key,
        user_profile=user_profile,
        years=user_profile.get("time_horizon", 10),
    )

    # LLM narrative
    try:
        explain_prompt = f"""You are a financial advisor explaining a stress test to an Indian investor.

Event: {simulation['event']}
Current corpus: ₹{current_corpus:,.0f}
Monthly SIP: ₹{monthly_sip:,.0f}
Without event: ₹{simulation['baseline_corpus']:,.0f} in {user_profile.get('time_horizon',10)} years
With event (median): ₹{simulation['stressed_p50']:,.0f}
Impact: ₹{abs(simulation['corpus_impact']):,.0f} {'less' if simulation['corpus_impact'] < 0 else 'more'}

Give 3 specific mitigation actions (under 20 words each). End with one encouraging sentence."""
        explanation = llm.invoke(explain_prompt).content
    except Exception:
        explanation = "Stress test completed. Please consult a financial advisor for detailed mitigation strategies."

    simulation["plain_english_explanation"] = explanation

    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "stress_test": simulation,
        }
    }
