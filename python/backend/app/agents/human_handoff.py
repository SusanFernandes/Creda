"""
Human Handoff agent — escalation from AI to human advisor.
Detects when human intervention is needed, prepares context, facilitates handoff.
"""
import logging
from typing import Any

from app.core.llm import fast_llm, invoke_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.human_handoff")

# Criteria for human escalation
_ESCALATION_TRIGGERS = {
    "high_value_portfolio": 1000000,  # ₹10 lakh+
    "complex_tax": ["capital gains", "foreign income", "business income", "multiple properties"],
    "emotional_distress": ["stressed", "worried", "panicking", "losing money", "bankruptcy", "debt trap"],
    "life_events": ["divorce", "death", "inheritance", "lawsuit", "medical emergency"],
    "regulatory": ["sebi complaint", "fraud", "mis-selling", "legal"],
}


async def run(state: FinancialState) -> dict[str, Any]:
    """Determine if human handoff is needed and prepare context."""
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}
    message = state.get("message", "").lower()

    # Check escalation triggers
    triggers_hit = []
    portfolio_value = portfolio.get("current_value", 0)
    if portfolio_value >= _ESCALATION_TRIGGERS["high_value_portfolio"]:
        triggers_hit.append(f"High-value portfolio (₹{portfolio_value:,.0f})")

    for keyword in _ESCALATION_TRIGGERS["complex_tax"]:
        if keyword in message:
            triggers_hit.append(f"Complex tax situation: {keyword}")
            break

    for keyword in _ESCALATION_TRIGGERS["emotional_distress"]:
        if keyword in message:
            triggers_hit.append(f"Emotional context detected: {keyword}")
            break

    for keyword in _ESCALATION_TRIGGERS["life_events"]:
        if keyword in message:
            triggers_hit.append(f"Major life event: {keyword}")
            break

    for keyword in _ESCALATION_TRIGGERS["regulatory"]:
        if keyword in message:
            triggers_hit.append(f"Regulatory concern: {keyword}")
            break

    needs_human = len(triggers_hit) > 0

    # Prepare context summary for advisor
    context_summary = {
        "user_age": profile.get("age"),
        "income": profile.get("monthly_income"),
        "risk_appetite": profile.get("risk_appetite"),
        "portfolio_value": portfolio_value,
        "original_query": state.get("message", ""),
        "triggers": triggers_hit,
        "conversation_history": state.get("history", [])[-5:],
    }

    # LLM generates empathetic response
    try:
        prompt = f"""The user said: "{state.get('message', '')}"
Escalation triggers: {triggers_hit}

If human handoff IS needed, respond empathetically acknowledging their situation and explain that you're connecting them with a SEBI-registered financial advisor who can help with this specific issue. Mention it will be done during business hours (Mon-Fri, 10AM-6PM IST).

If no triggers, provide a brief, helpful response and mention that human advisor support is available for complex situations.

Keep it warm and professional. Use ₹ in Indian context."""
        result = await invoke_llm(fast_llm, prompt)
        response = result.content.strip()
    except Exception:
        response = ("I understand this is a complex situation. Let me connect you with a "
                    "SEBI-registered advisor who can provide personalized guidance. "
                    "Available Mon-Fri, 10AM-6PM IST.")

    return {
        "needs_human": needs_human,
        "triggers": triggers_hit,
        "urgency": "high" if any("emotional" in t.lower() or "regulatory" in t.lower() for t in triggers_hit) else "normal",
        "context_for_advisor": context_summary,
        "response": response,
        "advisor_availability": "Mon-Fri, 10AM-6PM IST",
        "estimated_response_time": "Within 24 hours",
    }
