"""
Money Health Score Agent — 6-dimension financial health assessment.
Dimensions: Emergency Preparedness, Insurance Coverage, Investment Diversification,
            Debt Health, Tax Efficiency, Retirement Readiness.
"""

from __future__ import annotations
import logging
from typing import Dict, Any
from agents.state import FinancialState

logger = logging.getLogger(__name__)


def money_health_score_agent(state: FinancialState) -> dict:
    """LangGraph node — compute and return the 6-dimension Money Health Score."""
    profile = state.get("user_profile", {})
    portfolio = state.get("portfolio_data", {})

    income = max(1, profile.get("income", 1))  # avoid division by zero
    expenses = profile.get("expenses", income * 0.7)
    savings = profile.get("savings", 0)

    scores: Dict[str, Dict[str, Any]] = {}

    # ── 1. Emergency Preparedness (ideal = 6 months expenses) ──
    emergency_fund = profile.get("emergency_fund", savings * 0.2)
    emergency_needed = expenses * 6
    em_score = min(100, int(emergency_fund / emergency_needed * 100)) if emergency_needed else 0
    scores["emergency_preparedness"] = {
        "score": em_score,
        "current": emergency_fund,
        "target": emergency_needed,
        "status": "good" if em_score >= 80 else "needs_attention",
        "action": (
            f"Build ₹{max(0, emergency_needed - emergency_fund):,.0f} more in liquid savings"
            if em_score < 80
            else "Emergency fund is healthy"
        ),
    }

    # ── 2. Insurance Coverage ──
    life_cover = profile.get("life_insurance_cover", 0)
    recommended_life = income * 12 * 15
    ins_score = min(100, int(life_cover / recommended_life * 100)) if recommended_life else 0
    scores["insurance_coverage"] = {
        "score": ins_score,
        "current_life_cover": life_cover,
        "recommended_life_cover": recommended_life,
        "has_health_insurance": profile.get("has_health_insurance", False),
        "status": "good" if ins_score >= 60 else "critical",
        "action": (
            f"Get term insurance for ₹{max(0, recommended_life - life_cover):,.0f}"
            if ins_score < 60
            else "Life cover adequate"
        ),
    }

    # ── 3. Investment Diversification ──
    schemes = portfolio.get("schemes", [])
    categories = set(s.get("detected_category", "other") for s in schemes)
    div_score = min(100, len(categories) * 20) if schemes else 20
    scores["investment_diversification"] = {
        "score": div_score,
        "categories_present": list(categories),
        "fund_count": len(schemes),
        "status": "good" if div_score >= 60 else "needs_attention",
        "action": (
            "Good diversification" if div_score >= 60
            else "Add debt/hybrid funds for balance"
        ),
    }

    # ── 4. Debt Health (EMI / income < 40%) ──
    monthly_emi = profile.get("monthly_emi", 0)
    emi_ratio = monthly_emi / income if income else 0
    debt_score = max(0, 100 - int(emi_ratio * 250))
    scores["debt_health"] = {
        "score": debt_score,
        "emi_to_income_ratio": round(emi_ratio * 100, 1),
        "monthly_emi": monthly_emi,
        "status": "good" if emi_ratio < 0.35 else "critical",
        "action": (
            "EMI burden manageable" if emi_ratio < 0.35
            else f"EMI is {emi_ratio * 100:.0f}% of income — consider prepayment"
        ),
    }

    # ── 5. Tax Efficiency ──
    max_80c = 150_000
    current_80c = profile.get("investments_80c", profile.get("80c_investments", 0))
    tax_score = min(100, int(current_80c / max_80c * 100)) if max_80c else 0
    scores["tax_efficiency"] = {
        "score": tax_score,
        "80c_utilised": current_80c,
        "80c_remaining": max(0, max_80c - current_80c),
        "status": "good" if tax_score >= 80 else "needs_attention",
        "action": (
            f"Invest ₹{max(0, max_80c - current_80c):,.0f} more in 80C instruments"
            if current_80c < max_80c
            else "80C fully utilised"
        ),
    }

    # ── 6. Retirement Readiness ──
    age = profile.get("age", 30)
    retirement_age = 60
    years_left = max(1, retirement_age - age)
    corpus = portfolio.get("total_current_value", savings)
    retirement_needed = expenses * 12 * 25
    on_track = retirement_needed * max(0, age - 20) / max(1, retirement_age - 20)
    ret_score = min(100, int(corpus / on_track * 100)) if on_track else 30
    scores["retirement_readiness"] = {
        "score": ret_score,
        "current_corpus": corpus,
        "retirement_corpus_needed": round(retirement_needed, 0),
        "years_left": years_left,
        "status": "on_track" if ret_score >= 70 else "behind",
        "action": (
            "On track for retirement" if ret_score >= 70
            else f"Increase monthly investment to close the gap"
        ),
    }

    # ── Overall — weighted average ──
    weights = {
        "emergency_preparedness": 0.20,
        "insurance_coverage": 0.20,
        "investment_diversification": 0.15,
        "debt_health": 0.20,
        "tax_efficiency": 0.10,
        "retirement_readiness": 0.15,
    }
    overall = sum(scores[k]["score"] * weights[k] for k in scores)
    grade = "A" if overall >= 80 else "B" if overall >= 60 else "C" if overall >= 40 else "D"

    top_actions = [s["action"] for s in sorted(scores.values(), key=lambda x: x["score"])[:3]]

    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "money_health": {
                "overall_score": round(overall, 1),
                "grade": grade,
                "dimensions": scores,
                "top_3_actions": top_actions,
            },
        }
    }
