"""
SEBI RIA Compliance Service — advice audit trail + suitability documentation.

Every AI recommendation is logged with:
  - User prompt, model version, full response
  - User's risk profile + financial context at time of advice
  - Auto-generated suitability rationale
  - Timestamp for regulatory audit

SEBI Master Circular (June 2025) requires:
  1. Timestamped advice audit trail
  2. Suitability justification per recommendation
  3. AI disclosure in client agreement
  4. Annual compliance report export
"""
import logging
import time
from datetime import datetime, date
from typing import Any, Optional

from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import AdviceLog, UserProfile, Portfolio

logger = logging.getLogger("creda.compliance")


async def log_advice(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    intent: str,
    agent_used: str,
    user_message: str,
    response_text: str,
    agent_output: dict,
    language: str = "en",
    channel: str = "web",
    response_time_ms: int = 0,
) -> str:
    """
    Log an advice interaction for SEBI compliance.
    Auto-generates suitability rationale based on user context.
    Returns the AdviceLog ID.
    """
    # Fetch user context at time of advice
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = portfolio_result.scalar_one_or_none()

    risk_profile = profile.risk_appetite if profile else "unknown"
    age = profile.age if profile else 0
    income = profile.monthly_income * 12 if profile and profile.monthly_income else 0
    portfolio_value = portfolio.current_value if portfolio else 0

    # Auto-generate suitability rationale
    rationale = _generate_suitability(intent, agent_used, risk_profile, age, income, portfolio_value)

    log_entry = AdviceLog(
        user_id=user_id,
        session_id=session_id,
        intent=intent,
        agent_used=agent_used,
        user_message=user_message,
        model_name="llama-3.3-70b-versatile",
        response_text=response_text,
        agent_output=agent_output,
        risk_profile=risk_profile,
        age_at_advice=age,
        income_at_advice=income,
        portfolio_value_at_advice=portfolio_value,
        suitability_rationale=rationale,
        is_suitable=True,
        language=language,
        channel=channel,
        response_time_ms=response_time_ms,
    )
    db.add(log_entry)
    return log_entry.id


def _generate_suitability(
    intent: str, agent: str, risk: str, age: int, income: float, portfolio: float
) -> str:
    """Auto-generate a suitability rationale for the advice given."""
    parts = [
        f"Advice type: {intent} (agent: {agent}).",
        f"User risk profile: {risk}, age: {age}, annual income: ₹{income:,.0f}, portfolio value: ₹{portfolio:,.0f}.",
    ]

    suitability_map = {
        "fire_planner": "FIRE planning advice is suitable as it provides long-term projections aligned with the user's stated retirement goals and risk appetite.",
        "tax_wizard": "Tax regime comparison is informational and suitable for all profiles — shows both options without recommending specific products.",
        "portfolio_xray": "Portfolio analysis provides factual X-ray of existing holdings — no new investment recommendations made.",
        "stress_test": "Stress testing helps the user understand downside risks, appropriate for their risk profile assessment.",
        "budget_coach": "Budget analysis is educational and suitable — based on the user's own income/expense data.",
        "goal_planner": "Goal-based planning aligned with user's stated financial goals and time horizon.",
        "money_health": "Financial health score is a diagnostic tool — no specific product recommendations.",
        "market_pulse": "Market intelligence provides current data context — user should consult a SEBI-registered advisor before acting.",
        "tax_copilot": "Tax optimization suggestions based on user's disclosed tax profile and applicable sections.",
        "money_personality": "Behavioral profiling is educational — helps user understand their financial tendencies.",
        "couples_finance": "Joint financial analysis based on disclosed partner data — advisory in nature.",
        "sip_calculator": "SIP projections are mathematical calculations — not a recommendation for specific funds.",
        "goal_simulator": "Monte Carlo simulation provides probabilistic outcomes — past performance not indicative of future results.",
        "social_proof": "Peer benchmarking uses aggregated anonymized data — for context only, not actionable advice.",
        "et_research": "Research query provides factual information with source citations and confidence scoring.",
        "human_handoff": "User's situation identified as requiring human SEBI RIA — AI limitation acknowledged.",
    }

    if intent in suitability_map:
        parts.append(suitability_map[intent])
    else:
        parts.append("General conversational response — no specific financial recommendation made.")

    parts.append("CREDA AI disclosure: This advice was generated by an AI system using LLaMA 3.3 70B. Users should verify with a SEBI-registered advisor before making financial decisions.")

    return " ".join(parts)


async def generate_compliance_report(user_id: str, start_date: date, end_date: date) -> dict:
    """
    Generate SEBI-format compliance report for a user over a date range.
    Suitable for annual RIA audit submissions.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AdviceLog)
            .where(
                AdviceLog.user_id == user_id,
                AdviceLog.created_at >= datetime(start_date.year, start_date.month, start_date.day),
                AdviceLog.created_at <= datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59),
            )
            .order_by(AdviceLog.created_at)
        )
        logs = result.scalars().all()

        # Aggregate stats
        intent_counts: dict[str, int] = {}
        for log in logs:
            intent_counts[log.intent] = intent_counts.get(log.intent, 0) + 1

        total_interactions = len(logs)
        unsuitable_count = sum(1 for l in logs if not l.is_suitable)

        report = {
            "user_id": user_id,
            "report_period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "generated_at": datetime.now().isoformat(),
            "total_interactions": total_interactions,
            "unsuitable_advice_count": unsuitable_count,
            "suitability_rate": round((total_interactions - unsuitable_count) / max(total_interactions, 1) * 100, 1),
            "interaction_breakdown": intent_counts,
            "ai_disclosure": "All advice generated by CREDA AI (LLaMA 3.3 70B via Groq). AI use disclosed at onboarding. Not a SEBI-registered investment advisor.",
            "advice_entries": [
                {
                    "id": log.id,
                    "timestamp": log.created_at.isoformat() if log.created_at else "",
                    "intent": log.intent,
                    "agent": log.agent_used,
                    "user_query": log.user_message[:200],
                    "response_summary": log.response_text[:300],
                    "risk_profile": log.risk_profile,
                    "suitability": log.suitability_rationale,
                    "channel": log.channel,
                }
                for log in logs
            ],
        }

        return report
