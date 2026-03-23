"""
FIRE Planner Agent — Financial Independence / Retire Early calculator.
Computes FIRE number, required SIP, year-by-year roadmap, tax savings, and insurance gap.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List
from langchain_groq import ChatGroq
from agents.state import FinancialState

logger = logging.getLogger(__name__)


# ─── Core Calculations ───────────────────────────────────────────────────────

def calculate_fire_number(
    monthly_expenses: float,
    inflation_rate: float = 0.06,
    withdrawal_rate: float = 0.04,
    years_to_retirement: int = 20,
) -> dict:
    """FIRE corpus using the 4% rule, adjusted for Indian inflation."""
    future_monthly = monthly_expenses * ((1 + inflation_rate) ** years_to_retirement)
    future_annual = future_monthly * 12
    fire_corpus = future_annual / withdrawal_rate
    return {
        "fire_number": round(fire_corpus, 0),
        "future_monthly_expenses": round(future_monthly, 0),
        "years_to_retirement": years_to_retirement,
        "safe_withdrawal_rate_used": withdrawal_rate,
        "inflation_assumed": inflation_rate,
    }


def _calc_required_sip(target: float, current: float, years: int, rate: float = 0.12) -> float:
    months = years * 12
    monthly_rate = rate / 12
    fv_current = current * (1 + monthly_rate) ** months
    remaining = target - fv_current
    if remaining <= 0:
        return 0
    sip = remaining * monthly_rate / ((1 + monthly_rate) ** months - 1)
    return max(0, sip)


def generate_roadmap(
    current_savings: float,
    target_corpus: float,
    current_sip: float,
    years: int,
    expected_return: float = 0.12,
) -> List[Dict[str, Any]]:
    """Year-by-year milestone roadmap with 10% annual SIP step-up."""
    roadmap = []
    corpus = current_savings
    monthly_rate = expected_return / 12

    for year in range(1, min(years, 30) + 1):
        sip = current_sip * (1.10 ** (year - 1))
        for _ in range(12):
            corpus = corpus * (1 + monthly_rate) + sip
        pct = min(100, round(corpus / target_corpus * 100, 1)) if target_corpus else 0
        roadmap.append({
            "year": year,
            "corpus_projected": round(corpus, 0),
            "progress_pct": pct,
            "monthly_sip_this_year": round(sip, 0),
            "milestone": _milestone_label(pct),
        })
    return roadmap


def _milestone_label(pct: float) -> str:
    if pct >= 100:
        return "FIRE achieved!"
    if pct >= 75:
        return "Almost there"
    if pct >= 50:
        return "Halfway milestone"
    if pct >= 25:
        return "Good progress"
    return "Journey started"


# ─── Tax & Insurance Helpers ─────────────────────────────────────────────────

def _calculate_tax_savings(profile: dict) -> dict:
    annual_income = profile.get("income", 50000) * 12
    return {
        "80c_limit": 150000,
        "80c_instruments": ["ELSS (3yr lock-in, market returns)", "PPF (15yr, 7.1%)", "NPS Tier-1"],
        "nps_additional_80ccd": 50000,
        "hra_if_applicable": "Claim HRA if in rented accommodation",
        "total_potential_saving": min(annual_income * 0.30, 60000),
        "old_vs_new_regime": "Compare at filing — new regime simpler for income < ₹7L",
    }


def _check_insurance_gap(profile: dict) -> dict:
    annual_income = profile.get("income", 50000) * 12
    dependents = max(1, profile.get("dependents", 1))
    life_cover = annual_income * 15
    health_cover = 500000 * dependents
    age = profile.get("age", 30)
    return {
        "recommended_life_cover": life_cover,
        "recommended_health_cover": health_cover,
        "term_insurance_note": (
            f"Term insurance for ₹{life_cover:,.0f} at age {age} "
            f"costs ~₹{life_cover // 2000:,}/year"
        ),
    }


# ─── Agent Node ───────────────────────────────────────────────────────────────

def fire_planner_agent(state: FinancialState) -> dict:
    """LangGraph node — FIRE / retirement planning."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    profile = state.get("user_profile", {})

    age = profile.get("age", 30)
    income = profile.get("income", 50000)
    expenses = profile.get("expenses", income * 0.6)
    savings = profile.get("savings", 0)
    target_age = profile.get("target_retirement_age", 50)
    years = max(1, target_age - age)

    fire = calculate_fire_number(monthly_expenses=expenses, years_to_retirement=years)
    sip_needed = _calc_required_sip(target=fire["fire_number"], current=savings, years=years)
    roadmap = generate_roadmap(
        current_savings=savings,
        target_corpus=fire["fire_number"],
        current_sip=sip_needed,
        years=years,
    )

    result: Dict[str, Any] = {
        **fire,
        "current_savings": savings,
        "monthly_sip_required": round(sip_needed, 0),
        "monthly_sip_with_stepup": round(sip_needed * 0.7, 0),
        "roadmap": roadmap,
        "tax_optimisation": _calculate_tax_savings(profile),
        "insurance_gap": _check_insurance_gap(profile),
    }

    try:
        narrative_prompt = f"""Explain this FIRE plan to {profile.get('name','the user')} (age {age}) in simple language.

FIRE Number: ₹{fire['fire_number']:,.0f}
Monthly SIP needed: ₹{sip_needed:,.0f}
Years to goal: {years}
Current savings: ₹{savings:,.0f}

Keep under 100 words. Be specific. End with ONE action they can take TODAY."""
        result["narrative"] = llm.invoke(narrative_prompt).content
    except Exception as e:
        logger.error("FIRE narrative generation failed: %s", e)
        result["narrative"] = (
            f"Your FIRE target is ₹{fire['fire_number']:,.0f}. "
            f"Start a ₹{sip_needed:,.0f}/month SIP today to get there in {years} years."
        )

    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "fire_planner": result,
        }
    }
