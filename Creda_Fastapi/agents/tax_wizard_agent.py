"""
Tax Wizard Agent — compares Old vs New tax regime (FY 2024-25),
identifies missed deductions, and quantifies potential savings.
"""

from __future__ import annotations
import logging
from typing import Dict, Any
from langchain_groq import ChatGroq
from agents.state import FinancialState

logger = logging.getLogger(__name__)


# ─── Old Regime FY 2024-25 ────────────────────────────────────────────────────

def compute_tax_old_regime(gross_income: float, deductions: dict) -> dict:
    std = 50000
    sec_80c = min(deductions.get("80c", 0), 150000)
    sec_80ccd = min(deductions.get("80ccd", 0), 50000)
    sec_80d = min(deductions.get("80d", 0), 25000)
    hra = deductions.get("hra", 0)
    home_loan = min(deductions.get("home_loan_interest", 0), 200000)

    taxable = max(0, gross_income - std - sec_80c - sec_80ccd - sec_80d - hra - home_loan)

    if taxable <= 250_000:
        tax = 0
    elif taxable <= 500_000:
        tax = (taxable - 250_000) * 0.05
    elif taxable <= 1_000_000:
        tax = 12_500 + (taxable - 500_000) * 0.20
    else:
        tax = 112_500 + (taxable - 1_000_000) * 0.30

    # Rebate u/s 87A if taxable ≤ 5L
    if taxable <= 500_000:
        tax = 0

    tax_cess = tax * 1.04

    return {
        "gross_income": gross_income,
        "total_deductions": gross_income - taxable,
        "taxable_income": taxable,
        "tax_before_cess": round(tax, 0),
        "tax_with_cess": round(tax_cess, 0),
        "effective_rate": round(tax_cess / gross_income * 100, 2) if gross_income else 0,
        "regime": "old",
    }


# ─── New Regime FY 2024-25 ────────────────────────────────────────────────────

def compute_tax_new_regime(gross_income: float) -> dict:
    taxable = max(0, gross_income - 75_000)  # std deduction in new regime

    slabs = [
        (300_000, 0.00),
        (700_000, 0.05),
        (1_000_000, 0.10),
        (1_200_000, 0.15),
        (1_500_000, 0.20),
        (float("inf"), 0.30),
    ]

    tax = 0.0
    prev = 0
    for upper, rate in slabs:
        if taxable <= prev:
            break
        chunk = min(taxable, upper) - prev
        tax += chunk * rate
        prev = upper

    # Rebate u/s 87A for income ≤ ₹7L
    if gross_income <= 700_000:
        tax = 0

    tax_cess = tax * 1.04

    return {
        "gross_income": gross_income,
        "taxable_income": taxable,
        "tax_before_cess": round(tax, 0),
        "tax_with_cess": round(tax_cess, 0),
        "effective_rate": round(tax_cess / gross_income * 100, 2) if gross_income else 0,
        "regime": "new",
    }


# ─── Agent Node ───────────────────────────────────────────────────────────────

def tax_wizard_agent(state: FinancialState) -> dict:
    """LangGraph node — tax regime comparison + missed deductions finder."""
    profile = state.get("user_profile", {})
    annual_income = profile.get("income", 50000) * 12

    deductions: Dict[str, float] = {
        "80c": profile.get("investments_80c", profile.get("80c_investments", 0)),
        "80ccd": profile.get("nps_contribution", 0),
        "80d": profile.get("health_insurance_premium", 0),
        "hra": profile.get("hra", 0),
        "home_loan_interest": profile.get("home_loan_interest", 0),
    }

    old = compute_tax_old_regime(annual_income, deductions)
    new = compute_tax_new_regime(annual_income)

    better = "old" if old["tax_with_cess"] < new["tax_with_cess"] else "new"
    savings = abs(old["tax_with_cess"] - new["tax_with_cess"])

    missed = []
    if deductions["80c"] < 150_000:
        gap = 150_000 - deductions["80c"]
        missed.append(f"₹{gap:,.0f} unused 80C — invest in ELSS/PPF to save ₹{gap * 0.30:,.0f} in tax")
    if deductions["80ccd"] == 0:
        missed.append("NPS Tier-1 — invest ₹50,000 for extra ₹15,000 tax saving (80CCD(1B))")
    if deductions["80d"] == 0:
        missed.append("Health insurance premium — up to ₹25,000 deductible under 80D")

    recoverable = round(
        max(0, 150_000 - deductions["80c"]) * 0.30
        + (50_000 * 0.30 if deductions["80ccd"] == 0 else 0)
        + (25_000 * 0.30 if deductions["80d"] == 0 else 0),
        0,
    )

    result: Dict[str, Any] = {
        "old_regime": old,
        "new_regime": new,
        "recommended_regime": better,
        "annual_savings_by_switching": round(savings, 0),
        "missed_deductions": missed,
        "total_recoverable_tax": recoverable,
    }

    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "tax_wizard": result,
        }
    }
