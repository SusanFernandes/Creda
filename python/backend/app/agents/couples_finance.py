"""
Couples Finance agent — joint budgeting, HRA routing, NPS, insurance, combined net worth (CAMS + EPF).
Partner defaults from profile columns when API sends 0.
"""
from __future__ import annotations

import re
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
    message = (state.get("message") or "").lower()

    income1 = float(profile.get("monthly_income") or 0)
    expenses1 = float(profile.get("monthly_expenses") or 0)

    api_pi = _extract_partner_number(message, "income")
    api_pe = _extract_partner_number(message, "expense")
    partner_income = float(api_pi) if api_pi is not None else float(profile.get("partner_monthly_income") or 0)
    if partner_income <= 0:
        return profile_incomplete_payload(
            {"missing": ["partner_monthly_income"], "completeness_pct": 70.0, "is_complete": False}
        )
    partner_expenses = (
        float(api_pe) if api_pe is not None else float(profile.get("partner_monthly_expenses") or 0)
    )

    combined_income = income1 + partner_income
    combined_expenses = expenses1 + partner_expenses
    combined_savings = combined_income - combined_expenses

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

    data: dict[str, Any] = {
        "partner_name": profile.get("partner_name") or "Partner",
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

    rent = float(profile.get("rent_paid") or 0)
    basic1_m = float(profile.get("basic_salary") or 0)
    city = (profile.get("city") or "").lower()
    metro_cities = ["mumbai", "delhi", "kolkata", "chennai", "bangalore", "bengaluru", "hyderabad"]
    is_metro = bool(profile.get("is_metro")) or city in metro_cities
    hra_pct = 0.50 if is_metro else 0.40
    if rent > 0 and basic1_m > 0:
        basic1 = basic1_m * 12
        basic2 = max(partner_income * 12 * 0.45, 1.0)
        hra1 = max(0.0, min(rent * 12, rent * 12 - 0.10 * basic1, hra_pct * basic1))
        hra2 = max(0.0, min(rent * 12, rent * 12 - 0.10 * basic2, hra_pct * basic2))
        best = "Person 1 (you)" if hra1 >= hra2 else "Partner"
        data["hra_optimization"] = {
            "rent_annual": rent * 12,
            "hra_if_person1_claims": round(hra1),
            "hra_if_person2_claims": round(hra2),
            "recommended_claimer": best,
            "estimated_tax_saved_if_optimal_inr": round(max(hra1, hra2) * 0.30),
        }
    else:
        data["hra_optimization"] = {
            "note": "Add rent_paid and your basic_salary (monthly) for HRA comparison between partners.",
        }

    nps1 = float(profile.get("nps_contribution") or 0)
    nps2 = float(profile.get("partner_nps_contribution") or 0)
    data["nps_optimization"] = {
        "person1_nps": nps1,
        "person2_nps": nps2,
        "gap_to_max_each": max(50000 - nps1, 0),
        "combined_tax_saved_if_both_max_inr": round((max(0, 50000 - nps1) + max(0, 50000 - nps2)) * 0.30),
    }

    portfolio = state.get("portfolio_data") or {}
    cv = float(portfolio.get("current_value") or 0)
    savings1 = float(profile.get("savings") or 0)
    epf1 = float(profile.get("epf_balance") or 0)
    ppf1 = float(profile.get("ppf_balance") or 0)
    p2_saved_est = partner_income * 12 * 0.15
    data["combined_net_worth"] = {
        "person1_liquid_and_invested": round(savings1 + epf1 + ppf1 + cv),
        "partner_assets_estimated": round(p2_saved_est),
        "combined_estimate": round(savings1 + epf1 + ppf1 + cv + p2_saved_est),
        "note": "Partner assets estimated at ~15% of annual income if no linked portfolio.",
    }

    life_cover1 = float(profile.get("life_insurance_cover") or 0)
    has_health1 = bool(profile.get("has_health_insurance"))
    combined_annual_income = combined_income * 12
    recommended_life = combined_annual_income * 10
    data["insurance_analysis"] = {
        "person1_life_cover": life_cover1,
        "recommended_combined_cover": round(recommended_life),
        "person1_has_health": has_health1,
        "family_floater_tip": "Family floater often saves 20–40% vs two individual health plans at same cover.",
    }

    br1 = (profile.get("partner_tax_bracket") or "").strip()
    data["sip_split_tax_hint"] = {
        "person1_bracket_guess": br1 or "unknown",
        "tip": "Higher bracket partner can bias debt/indexation-heavy funds; lower bracket can hold more equity LTCG.",
    }

    try:
        result = await primary_llm.ainvoke(_COUPLES_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_couples_finance(
    profile,
    partner_income: float,
    partner_expenses: float,
    split_strategy: str,
    language: str,
    voice_mode: bool,
    portfolio_dict: dict | None = None,
) -> dict:
    from app.agents.synthesizer import synthesize

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    if partner_income and partner_income > 0:
        profile_dict["partner_monthly_income"] = partner_income
    if partner_expenses and partner_expenses > 0:
        profile_dict["partner_monthly_expenses"] = partner_expenses

    state: FinancialState = {
        "user_id": profile.user_id,
        "message": f"couples finance partner_income={partner_income} partner_expenses={partner_expenses}",
        "intent": "couples_finance",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
        "portfolio_data": portfolio_dict,
    }
    output = await run(state)
    response = await synthesize(output, "couples_finance", "couples finance", language, voice_mode)
    return {"analysis": output, "response": response}


def _extract_partner_number(message: str, field: str) -> float | None:
    msg = message.lower()
    match = re.search(rf"partner[_\s]*{field}\s*[=:]\s*([\d,]+\.?\d*)", msg)
    if match:
        return float(match.group(1).replace(",", ""))
    patterns = [
        rf"(?:partner|spouse|husband|wife)(?:'s)?\s*{field}[s]?\s*(?:is|=|:)?\s*(?:₹|rs\.?)?\s*([\d,]+\.?\d*)",
        rf"(?:partner|spouse|husband|wife)\s*(?:earns?|makes?|gets?)\s*(?:₹|rs\.?)?\s*([\d,]+\.?\d*)",
    ]
    for pat in patterns:
        m = re.search(pat, msg)
        if m:
            val = float(m.group(1).replace(",", ""))
            if "lakh" in msg or "lac" in msg:
                val *= 100000
            return val
    return None
