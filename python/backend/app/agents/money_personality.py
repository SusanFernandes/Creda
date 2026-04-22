"""
Money Personality agent — behavioral finance profiling.
Determines user's financial personality type and customizes advice accordingly.
"""
import logging
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.money_personality")

# 6 Money Personality archetypes based on behavioral finance research
_PERSONALITIES = {
    "cautious_planner": {
        "name": "Cautious Planner",
        "emoji": "🛡️",
        "traits": ["Loss-averse", "Prefers guaranteed returns", "Methodical decision-maker"],
        "strengths": ["Consistent savings habit", "Low debt tendency", "Good emergency planning"],
        "blind_spots": ["Under-allocation to equity", "Missing growth opportunities", "Over-insurance"],
        "ideal_products": ["PPF", "Fixed Deposits", "Debt Mutual Funds", "Index Funds (small allocation)"],
        "nudge_style": "reassuring",
    },
    "growth_seeker": {
        "name": "Growth Seeker",
        "emoji": "🚀",
        "traits": ["High risk tolerance", "Trend-follower", "Optimistic about markets"],
        "strengths": ["Early equity adoption", "Good at compounding", "Goal-oriented"],
        "blind_spots": ["Concentration risk", "Ignoring insurance", "Chasing returns"],
        "ideal_products": ["Small/Mid Cap Funds", "Direct Equity", "NPS Tier-2", "REITs"],
        "nudge_style": "challenging",
    },
    "balanced_pragmatist": {
        "name": "Balanced Pragmatist",
        "emoji": "⚖️",
        "traits": ["Moderate risk appetite", "Data-driven", "Values diversification"],
        "strengths": ["Well-diversified portfolio", "Good asset allocation", "Systematic investor"],
        "blind_spots": ["Analysis paralysis", "Delayed decisions", "Over-diversification"],
        "ideal_products": ["Balanced Advantage Funds", "Multi-Asset Allocation", "NPS", "ELSS"],
        "nudge_style": "analytical",
    },
    "security_first": {
        "name": "Security First",
        "emoji": "🏠",
        "traits": ["Family-oriented", "Insurance-heavy", "Prefers real assets"],
        "strengths": ["Strong safety net", "Good insurance coverage", "Stable financial base"],
        "blind_spots": ["Low equity allocation", "Real estate concentration", "Missing inflation hedge"],
        "ideal_products": ["Term Insurance", "Health Insurance", "Gold ETFs", "Conservative Hybrid Funds"],
        "nudge_style": "supportive",
    },
    "wealth_builder": {
        "name": "Wealth Builder",
        "emoji": "📈",
        "traits": ["Long-term thinker", "Tax-efficient", "FIRE-inclined"],
        "strengths": ["Maximizes tax deductions", "High savings rate", "Goal-based investing"],
        "blind_spots": ["Over-optimization", "Missing present enjoyment", "Complex portfolio"],
        "ideal_products": ["ELSS", "Index Funds", "NPS (80CCD)", "Direct Equity (bluechips)"],
        "nudge_style": "strategic",
    },
    "impulse_spender": {
        "name": "Mindful Spender",
        "emoji": "💡",
        "traits": ["Present-focused", "Lifestyle-driven", "Irregular saver"],
        "strengths": ["High earning potential", "Adaptable", "Experiential mindset"],
        "blind_spots": ["Low emergency fund", "No systematic investment", "Lifestyle inflation"],
        "ideal_products": ["Auto-debit SIPs", "Liquid Funds (parking)", "Micro-goals", "Budget tracking"],
        "nudge_style": "motivational",
    },
}

_PERSONALITY_PROMPT = """You are a behavioral finance expert. Analyze this user's financial profile and determine their Money Personality type.

Profile data:
{profile}

Portfolio data:
{portfolio}

Personality types: {types}

Determine which personality BEST fits this user based on:
- Risk appetite and investment choices
- Savings rate (income vs expenses)
- Insurance coverage
- Emergency fund adequacy
- Investment patterns (equity vs debt, direct vs regular)

Respond with EXACTLY this JSON format (no markdown):
{{"primary_type": "<type_key>", "secondary_type": "<type_key>", "confidence": <0-100>, "reasoning": "<2-3 sentences>"}}

Valid type keys: {type_keys}"""


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    # Heuristic pre-classification
    risk = profile.get("risk_appetite", "moderate")
    savings_rate = 0
    income = profile.get("monthly_income", 0)
    expenses = profile.get("monthly_expenses", 0)
    if income > 0:
        savings_rate = (income - expenses) / income * 100

    has_insurance = profile.get("has_health_insurance", False)
    emergency = profile.get("emergency_fund", 0)
    emergency_months = emergency / expenses if expenses > 0 else 0

    # Quick heuristic
    heuristic_type = "balanced_pragmatist"
    if risk == "aggressive" and savings_rate > 30:
        heuristic_type = "wealth_builder"
    elif risk == "aggressive":
        heuristic_type = "growth_seeker"
    elif risk == "conservative" and has_insurance:
        heuristic_type = "security_first"
    elif risk == "conservative":
        heuristic_type = "cautious_planner"
    elif savings_rate < 10:
        heuristic_type = "impulse_spender"

    # LLM refinement
    try:
        import json
        result = await fast_llm.ainvoke(_PERSONALITY_PROMPT.format(
            profile=str({k: profile.get(k) for k in [
                "age", "monthly_income", "monthly_expenses", "risk_appetite",
                "savings", "emergency_fund", "has_health_insurance",
                "life_insurance_cover", "investments_80c", "nps_contribution",
            ]}),
            portfolio=str({"funds_count": len(portfolio.get("funds", [])),
                          "total_value": portfolio.get("current_value", 0)}),
            types=", ".join(f"{k}: {v['name']}" for k, v in _PERSONALITIES.items()),
            type_keys=", ".join(_PERSONALITIES.keys()),
        ))
        parsed = json.loads(result.content.strip())
        primary_type = parsed.get("primary_type", heuristic_type)
        secondary_type = parsed.get("secondary_type", heuristic_type)
        confidence = parsed.get("confidence", 70)
        reasoning = parsed.get("reasoning", "")
    except Exception:
        from app.core.llm import fast_llm  # noqa: reimport for safety
        primary_type = heuristic_type
        secondary_type = heuristic_type
        confidence = 65
        reasoning = "Based on profile analysis."

    if primary_type not in _PERSONALITIES:
        primary_type = heuristic_type

    personality = _PERSONALITIES[primary_type]

    return {
        "primary_type": primary_type,
        "secondary_type": secondary_type,
        "personality": personality,
        "confidence": confidence,
        "reasoning": reasoning,
        "savings_rate": round(savings_rate, 1),
        "emergency_months": round(emergency_months, 1),
        "has_insurance": has_insurance,
        "all_types": {k: {"name": v["name"], "emoji": v["emoji"]} for k, v in _PERSONALITIES.items()},
    }


async def run_money_personality(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": "money personality assessment",
        "intent": "money_personality",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "money_personality", "personality assessment", language, voice_mode)
    return {"analysis": output, "response": response}
