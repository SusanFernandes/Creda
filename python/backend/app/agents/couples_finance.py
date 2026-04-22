"""
Couples Finance agent — joint budgeting, expense splitting, combined planning.
"""
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_COUPLES_PROMPT = """You are a couples finance advisor for Indian partners. Given this analysis:
1. Recommend the best expense-splitting strategy for this couple
2. Identify the biggest financial risk as a couple
3. Suggest one joint goal they should prioritize

Data:
{data}

Be practical and sensitive to relationship dynamics. Use ₹ amounts."""


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}

    income1 = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)

    # Partner data: try structured extraction, then natural language
    message = state.get("message", "")
    partner_income = _extract_partner_number(message, "income") or income1 * 0.8
    partner_expenses = _extract_partner_number(message, "expense") or expenses * 0.5

    combined_income = income1 + partner_income
    combined_expenses = expenses + partner_expenses
    combined_savings = combined_income - combined_expenses

    # Split strategies
    proportional_share1 = income1 / combined_income if combined_income > 0 else 0.5
    proportional_share2 = 1 - proportional_share1

    strategies = {
        "proportional": {
            "description": "Each pays based on income ratio",
            "person1_pays": round(combined_expenses * proportional_share1),
            "person2_pays": round(combined_expenses * proportional_share2),
            "person1_keeps": round(income1 - combined_expenses * proportional_share1),
            "person2_keeps": round(partner_income - combined_expenses * proportional_share2),
        },
        "50_50": {
            "description": "Equal split",
            "person1_pays": round(combined_expenses / 2),
            "person2_pays": round(combined_expenses / 2),
            "person1_keeps": round(income1 - combined_expenses / 2),
            "person2_keeps": round(partner_income - combined_expenses / 2),
        },
        "yours_mine_ours": {
            "description": "Pool 70% for shared, keep 30% personal",
            "shared_pool": round(combined_income * 0.70),
            "person1_personal": round(income1 * 0.30),
            "person2_personal": round(partner_income * 0.30),
        },
    }

    data = {
        "person1_income": income1,
        "person2_income": round(partner_income),
        "combined_income": round(combined_income),
        "combined_expenses": round(combined_expenses),
        "combined_savings": round(combined_savings),
        "savings_rate": round(combined_savings / combined_income * 100, 1) if combined_income > 0 else 0,
        "income_ratio": f"{proportional_share1:.0%} / {proportional_share2:.0%}",
        "strategies": strategies,
        "recommended": "proportional" if abs(income1 - partner_income) > combined_income * 0.2 else "50_50",
    }

    try:
        result = await primary_llm.ainvoke(_COUPLES_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_couples_finance(profile, partner_income: float, partner_expenses: float,
                               split_strategy: str, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id,
        "message": f"couples finance partner_income={partner_income} partner_expenses={partner_expenses}",
        "intent": "couples_finance",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "couples_finance", "couples finance", language, voice_mode)
    return {"analysis": output, "response": response}


def _extract_partner_number(message: str, field: str) -> float | None:
    """Extract partner financial data from natural language or key=value format."""
    import re
    msg = message.lower()

    # Try key=value format first: "partner_income=50000"
    match = re.search(rf"partner[_\s]*{field}\s*[=:]\s*([\d,]+\.?\d*)", msg)
    if match:
        return float(match.group(1).replace(",", ""))

    # Natural language: "partner earns 50000" / "spouse income is 80k" / "partner's salary 1.2 lakh"
    patterns = [
        rf"(?:partner|spouse|husband|wife)(?:'s)?\s*{field}[s]?\s*(?:is|=|:)?\s*(?:₹|rs\.?)?\s*([\d,]+\.?\d*)",
        rf"(?:partner|spouse|husband|wife)\s*(?:earns?|makes?|gets?)\s*(?:₹|rs\.?)?\s*([\d,]+\.?\d*)",
        rf"(?:partner|spouse|husband|wife)(?:'s)?\s*(?:monthly\s*)?(?:{field}|salary|earning)\s*(?:is|=|:)?\s*(?:₹|rs\.?)?\s*([\d,]+\.?\d*)",
    ]
    for pat in patterns:
        m = re.search(pat, msg)
        if m:
            val = float(m.group(1).replace(",", ""))
            if "lakh" in msg or "lac" in msg:
                val *= 100000
            elif "k" in msg[m.end():m.end()+2]:
                val *= 1000
            return val
    return None
