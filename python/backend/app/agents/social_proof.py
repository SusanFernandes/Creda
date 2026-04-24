"""
Social Proof agent — anonymized crowd wisdom, peer benchmarking.
"78% of users in your age group increased SIPs after the last correction."
Uses real DB aggregation when enough users exist, falls back to curated benchmarks.
"""
import logging
from typing import Any

from sqlalchemy import select, func as sqlfunc, and_, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.social_proof")

# Curated fallback benchmarks (used when <5 users in age group)
_FALLBACK_BENCHMARKS = {
    "20-30": {
        "avg_savings_rate": 22, "avg_sip": 8000, "avg_emergency_months": 2.5,
        "top_funds": ["Nifty 50 Index", "Parag Parikh Flexi Cap", "Mirae Asset Large Cap"],
        "avg_equity_pct": 75, "insurance_adoption": 45,
        "behavior": "78% increased SIPs after market corrections",
        "sample_size": 0,
    },
    "30-40": {
        "avg_savings_rate": 28, "avg_sip": 18000, "avg_emergency_months": 4.2,
        "top_funds": ["HDFC Balanced Advantage", "SBI Bluechip", "Axis Midcap"],
        "avg_equity_pct": 65, "insurance_adoption": 72,
        "behavior": "65% have started FIRE planning in this age group",
        "sample_size": 0,
    },
    "40-50": {
        "avg_savings_rate": 32, "avg_sip": 28000, "avg_emergency_months": 6.1,
        "top_funds": ["ICICI Pru Equity & Debt", "Kotak Flexicap", "HDFC Top 100"],
        "avg_equity_pct": 55, "insurance_adoption": 88,
        "behavior": "72% shifted to direct plans for lower expense ratios",
        "sample_size": 0,
    },
    "50+": {
        "avg_savings_rate": 35, "avg_sip": 22000, "avg_emergency_months": 8.5,
        "top_funds": ["SBI Magnum Gilt", "HDFC Corporate Bond", "Aditya Birla Sun Life Savings"],
        "avg_equity_pct": 35, "insurance_adoption": 92,
        "behavior": "85% have adequate health insurance in this group",
        "sample_size": 0,
    },
}


async def _get_real_peer_benchmarks(age_group: str, db: AsyncSession) -> dict | None:
    """Query real anonymized peer data from DB. Returns None if too few users."""
    from app.models import UserProfile

    age_ranges = {"20-30": (20, 30), "30-40": (30, 40), "40-50": (40, 50), "50+": (50, 100)}
    age_min, age_max = age_ranges.get(age_group, (20, 100))

    try:
        result = await db.execute(
            select(
                sqlfunc.count(UserProfile.id).label("count"),
                sqlfunc.avg(UserProfile.monthly_income).label("avg_income"),
                sqlfunc.avg(UserProfile.monthly_expenses).label("avg_expenses"),
                sqlfunc.avg(UserProfile.emergency_fund).label("avg_emergency"),
                sqlfunc.sum(
                    sqlfunc.cast(UserProfile.has_health_insurance, Integer)
                ).label("insured_count"),
            ).where(
                and_(
                    UserProfile.age >= age_min,
                    UserProfile.age < age_max,
                    UserProfile.onboarding_complete == True,
                )
            )
        )
        row = result.one()
        count = row.count or 0

        # Need at least 5 users for meaningful peer data
        if count < 5:
            return None

        avg_income = row.avg_income or 0
        avg_expenses = row.avg_expenses or 0
        avg_emergency = row.avg_emergency or 0
        insured = row.insured_count or 0
        savings_rate = round((avg_income - avg_expenses) / avg_income * 100, 1) if avg_income > 0 else 0
        emergency_months = round(avg_emergency / avg_expenses, 1) if avg_expenses > 0 else 0

        return {
            "avg_savings_rate": savings_rate,
            "avg_sip": round((avg_income - avg_expenses) * 0.5),  # Assume ~50% of savings goes to SIP
            "avg_emergency_months": emergency_months,
            "top_funds": _FALLBACK_BENCHMARKS.get(age_group, {}).get("top_funds", []),
            "avg_equity_pct": _FALLBACK_BENCHMARKS.get(age_group, {}).get("avg_equity_pct", 60),
            "insurance_adoption": round(insured / count * 100) if count > 0 else 0,
            "behavior": _FALLBACK_BENCHMARKS.get(age_group, {}).get("behavior", ""),
            "sample_size": count,
        }
    except Exception as e:
        logger.warning("DB peer query failed: %s", e)
        return None

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
    from app.agents.profile_checks import require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    age = profile.get("age")
    age_group = _get_age_group(age)

    # Try real DB aggregation first, fall back to curated benchmarks
    peers = None
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db_session:
            peers = await _get_real_peer_benchmarks(age_group, db_session)
    except Exception as e:
        logger.warning("Could not query peer benchmarks from DB: %s", e)
    if peers is None:
        peers = _FALLBACK_BENCHMARKS.get(age_group, _FALLBACK_BENCHMARKS["30-40"])

    income = profile.get("monthly_income")
    expenses = profile.get("monthly_expenses")
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

    if not insights:
        cmp_sr = comparisons["savings_rate"]
        cmp_ef = comparisons["emergency_fund"]
        insights = (
            f"Peer snapshot ({age_group}): typical savings rate ~{peers['avg_savings_rate']}%; "
            f"you are at {user_metrics['savings_rate']}% — {'ahead of' if cmp_sr['status'] == 'above' else 'behind' if cmp_sr['status'] == 'below' else 'aligned with'} the band. "
            f"Emergency buffer: peers ~{peers['avg_emergency_months']} months vs your ~{user_metrics['emergency_months']} months ({cmp_ef['status']}). "
            f"Insight: {peers['behavior']}"
        )

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
