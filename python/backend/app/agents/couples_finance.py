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
    from app.agents.profile_checks import profile_incomplete_payload, require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    profile = state.get("user_profile") or {}

    income1 = profile.get("monthly_income")
    expenses = profile.get("monthly_expenses")

    # Partner data: try structured extraction, then natural language
    message = state.get("message", "")
    partner_income = _extract_partner_number(message, "income") or profile.get("partner_monthly_income")
    partner_expenses = _extract_partner_number(message, "expense")
    if partner_income is None:
        return profile_incomplete_payload(
            {"missing": ["partner_monthly_income"], "completeness_pct": 70.0, "is_complete": False}
        )
    if partner_expenses is None:
        partner_expenses = 0.0

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

    # HRA claim optimization — route HRA through the partner paying more rent
    rent = profile.get("rent_paid", 0)
    city = profile.get("city", "").lower()
    metro_cities = ["mumbai", "delhi", "kolkata", "chennai", "bangalore", "bengaluru", "hyderabad"]
    hra_pct = 0.50 if city in metro_cities else 0.40
    if rent > 0:
        basic1 = income1 * 12 * 0.4
        basic2 = partner_income * 12 * 0.4
        hra1 = min(rent * 12, rent * 12 - 0.10 * basic1, hra_pct * basic1)
        hra2 = min(rent * 12, rent * 12 - 0.10 * basic2, hra_pct * basic2)
        hra1 = max(hra1, 0)
        hra2 = max(hra2, 0)
        best_claimer = "Person 1" if hra1 >= hra2 else "Person 2"
        hra_savings = max(hra1, hra2) * 0.30  # assume 30% bracket
        data["hra_optimization"] = {
            "rent_annual": rent * 12,
            "hra_if_person1_claims": round(hra1),
            "hra_if_person2_claims": round(hra2),
            "recommended_claimer": best_claimer,
            "tax_saved": round(hra_savings),
            "tip": f"Route rent agreement to {best_claimer} for ₹{hra_savings:,.0f} extra tax saving.",
        }

    # NPS matching optimization
    nps1 = profile.get("nps_contribution", 0)
    data["nps_optimization"] = {
        "person1_nps": nps1,
        "gap_to_max": max(50000 - nps1, 0),
        "combined_nps_potential": 100000,
        "tax_saved_if_both_max": round(100000 * 0.30),
        "tip": "Both partners should invest ₹50K each in NPS for ₹30K combined tax saving under 80CCD(1B).",
    }

    # Joint insurance analysis
    life_cover1 = profile.get("life_insurance_cover", 0)
    has_health1 = profile.get("has_health_insurance", False)
    combined_annual_income = combined_income * 12
    recommended_life = combined_annual_income * 10  # 10x combined for couples
    data["insurance_analysis"] = {
        "person1_life_cover": life_cover1,
        "recommended_combined_cover": round(recommended_life),
        "person1_has_health": has_health1,
        "recommended_family_floater": 1000000,  # ₹10L
        "tip": "Get a family floater health policy (₹10L cover) — cheaper than 2 individual plans. "
               f"Combined term life should be ₹{recommended_life:,.0f} (10x combined income).",
    }

    # Combined net worth
    savings1 = profile.get("savings", 0)
    epf1 = profile.get("epf_balance", 0)
    ppf1 = profile.get("ppf_balance", 0)
    portfolio1 = profile.get("portfolio_value", 0) if profile.get("portfolio_value") else 0
    data["combined_net_worth"] = {
        "person1_assets": round(savings1 + epf1 + ppf1 + portfolio1),
        "person2_assets_estimated": round(partner_income * 12 * 0.15),  # estimate: 15% of annual income saved
        "combined_estimate": round(savings1 + epf1 + ppf1 + portfolio1 + partner_income * 12 * 0.15),
        "combined_annual_savings_potential": round(combined_savings * 12),
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
