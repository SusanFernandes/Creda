"""
Social Proof agent — anonymized crowd wisdom, peer benchmarking.
"78% of users in your age group increased SIPs after the last correction."
"""
import logging
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.social_proof")

# Pre-computed peer benchmarks (in production, these come from DB aggregates)
_PEER_BENCHMARKS = {
    "20-30": {
        "avg_savings_rate": 22, "avg_sip": 8000, "avg_emergency_months": 2.5,
        "top_funds": ["Nifty 50 Index", "Parag Parikh Flexi Cap", "Mirae Asset Large Cap"],
        "avg_equity_pct": 75, "insurance_adoption": 45,
        "behavior": "78% increased SIPs after market corrections",
    },
    "30-40": {
        "avg_savings_rate": 28, "avg_sip": 18000, "avg_emergency_months": 4.2,
        "top_funds": ["HDFC Balanced Advantage", "SBI Bluechip", "Axis Midcap"],
        "avg_equity_pct": 65, "insurance_adoption": 72,
        "behavior": "65% have started FIRE planning in this age group",
    },
    "40-50": {
        "avg_savings_rate": 32, "avg_sip": 28000, "avg_emergency_months": 6.1,
        "top_funds": ["ICICI Pru Equity & Debt", "Kotak Flexicap", "HDFC Top 100"],
        "avg_equity_pct": 55, "insurance_adoption": 88,
        "behavior": "72% shifted to direct plans for lower expense ratios",
    },
    "50+": {
        "avg_savings_rate": 35, "avg_sip": 22000, "avg_emergency_months": 8.5,
        "top_funds": ["SBI Magnum Gilt", "HDFC Corporate Bond", "Aditya Birla Sun Life Savings"],
        "avg_equity_pct": 35, "insurance_adoption": 92,
        "behavior": "85% have adequate health insurance in this group",
    },
}

_SOCIAL_PROMPT = """You are a peer comparison analyst for Indian investors.
Given the user's profile and their peer group benchmarks, provide:
1. How they compare (better/worse/on par) in 3 key areas
2. One inspiring insight from their peer group
3. One area where they're behind and a specific action to catch up

User: {user}
Peer group ({age_group}): {peers}

Be encouraging but honest. Use ₹ amounts. Never reveal individual user data."""


def _get_age_group(age: int) -> str:
    if age < 30:
        return "20-30"
    if age < 40:
        return "30-40"
    if age < 50:
        return "40-50"
    return "50+"


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    age = profile.get("age", 30)
    age_group = _get_age_group(age)
    peers = _PEER_BENCHMARKS.get(age_group, _PEER_BENCHMARKS["30-40"])

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
    emergency = profile.get("emergency_fund", 0)
    emergency_months = emergency / expenses if expenses > 0 else 0

    user_metrics = {
        "savings_rate": round(savings_rate, 1),
        "emergency_months": round(emergency_months, 1),
        "has_insurance": profile.get("has_health_insurance", False),
        "portfolio_value": portfolio.get("current_value", 0),
        "funds_count": len(portfolio.get("funds", [])),
        "risk_appetite": profile.get("risk_appetite", "moderate"),
    }

    # Comparison
    comparisons = {
        "savings_rate": {
            "you": user_metrics["savings_rate"],
            "peers": peers["avg_savings_rate"],
            "status": "above" if user_metrics["savings_rate"] > peers["avg_savings_rate"] else "below",
        },
        "emergency_fund": {
            "you": f"{user_metrics['emergency_months']} months",
            "peers": f"{peers['avg_emergency_months']} months",
            "status": "above" if user_metrics["emergency_months"] > peers["avg_emergency_months"] else "below",
        },
        "insurance": {
            "you": "Yes" if user_metrics["has_insurance"] else "No",
            "peers": f"{peers['insurance_adoption']}% have insurance",
            "status": "on_par" if user_metrics["has_insurance"] else "below",
        },
    }

    try:
        result = await primary_llm.ainvoke(_SOCIAL_PROMPT.format(
            user=str(user_metrics),
            age_group=age_group,
            peers=str(peers),
        ))
        insights = result.content.strip()
    except Exception:
        insights = ""

    return {
        "age_group": age_group,
        "peer_benchmarks": peers,
        "your_metrics": user_metrics,
        "comparisons": comparisons,
        "peer_trend": peers["behavior"],
        "top_peer_funds": peers["top_funds"],
        "insights": insights,
    }


async def run_social_proof(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": "peer comparison",
        "intent": "social_proof",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "social_proof", "peer benchmarking", language, voice_mode)
    return {"analysis": output, "response": response}
