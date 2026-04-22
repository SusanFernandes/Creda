"""
FIRE Planner agent — Financial Independence Retire Early.
Computes FIRE number, required SIP, 30-year roadmap, tax optimisation, insurance gaps.
"""
import math
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_FIRE_PROMPT = """You are a FIRE (Financial Independence Retire Early) expert for Indian investors.
Given the calculations below, provide a concise FIRE plan with:
1. Whether the user is on track or behind
2. Key actions to accelerate FIRE (max 3)
3. Tax-saving opportunities they're missing
4. Insurance gaps

Data:
{data}

Be specific with ₹ amounts and timelines."""


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    age = profile.get("age", 30)
    fire_target_age = profile.get("fire_target_age", 55)
    savings = profile.get("savings", 0)
    epf = profile.get("epf_balance", 0)
    nps = profile.get("nps_balance", 0)
    ppf = profile.get("ppf_balance", 0)

    annual_expenses = expenses * 12
    inflation_rate = 0.06
    real_return = 0.06  # 12% nominal - 6% inflation

    # FIRE number (4% rule, inflation-adjusted)
    years_to_fire = max(fire_target_age - age, 1)
    future_annual_expenses = annual_expenses * ((1 + inflation_rate) ** years_to_fire)
    fire_number = future_annual_expenses / 0.04

    # Current corpus
    portfolio = state.get("portfolio_data") or {}
    current_corpus = (
        (portfolio.get("current_value") or 0) + savings + epf + nps + ppf
    )

    # Required SIP (Future Value of Annuity formula)
    monthly_return = real_return / 12
    months = years_to_fire * 12
    if monthly_return > 0 and months > 0:
        # FV of current corpus
        fv_current = current_corpus * ((1 + real_return) ** years_to_fire)
        gap = max(fire_number - fv_current, 0)
        # Required monthly SIP to fill the gap
        if gap > 0:
            required_sip = gap * monthly_return / (((1 + monthly_return) ** months) - 1)
        else:
            required_sip = 0
    else:
        fv_current = current_corpus
        required_sip = 0

    current_sip = income - expenses
    sip_gap = max(required_sip - current_sip, 0)

    # 30-year roadmap with 10% annual step-up
    roadmap = []
    projected_corpus = current_corpus
    annual_sip = current_sip * 12
    for year in range(1, min(years_to_fire + 1, 31)):
        projected_corpus = projected_corpus * (1 + real_return) + annual_sip
        roadmap.append({
            "year": year,
            "age": age + year,
            "corpus": round(projected_corpus),
            "annual_sip": round(annual_sip),
        })
        annual_sip *= 1.10  # 10% step-up

    # Tax optimisation check
    investments_80c = profile.get("investments_80c", 0)
    nps_contribution = profile.get("nps_contribution", 0)
    tax_gaps = []
    if investments_80c < 150000:
        tax_gaps.append(f"80C: ₹{150000 - investments_80c:,.0f} unused of ₹1.5L limit")
    if nps_contribution < 50000:
        tax_gaps.append(f"80CCD(1B): ₹{50000 - nps_contribution:,.0f} additional NPS deduction available")
    if not profile.get("has_health_insurance"):
        tax_gaps.append("80D: No health insurance — missing ₹25,000 deduction + health coverage")

    # Insurance gap
    insurance_gaps = []
    life_cover = profile.get("life_insurance_cover", 0)
    recommended_cover = income * 12 * 15  # 15x annual income
    if life_cover < recommended_cover:
        insurance_gaps.append(f"Term life: ₹{(recommended_cover - life_cover):,.0f} additional cover needed (target: 15x annual income)")

    data = {
        "fire_number": round(fire_number),
        "current_corpus": round(current_corpus),
        "gap": round(max(fire_number - fv_current, 0)),
        "years_to_fire": years_to_fire,
        "target_age": fire_target_age,
        "required_sip": round(required_sip),
        "current_sip": current_sip,
        "sip_gap": round(sip_gap),
        "on_track": required_sip <= current_sip,
        "roadmap_summary": roadmap[:5],  # first 5 years
        "tax_gaps": tax_gaps,
        "insurance_gaps": insurance_gaps,
    }

    # LLM enrichment
    try:
        result = await primary_llm.ainvoke(_FIRE_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_fire_planner(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "FIRE plan", "intent": "fire_planner",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "fire_planner", "FIRE plan", language, voice_mode)
    return {"analysis": output, "response": response}
