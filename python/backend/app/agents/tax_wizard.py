"""
Tax Wizard agent — Old vs New regime comparison, missed deductions, recovery amounts.
FY2024-25 rules.
"""
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

# FY2024-25 tax slabs
_OLD_SLABS = [(250000, 0), (500000, 0.05), (1000000, 0.20), (float("inf"), 0.30)]
_NEW_SLABS = [(300000, 0), (700000, 0.05), (1000000, 0.10), (1200000, 0.15), (1500000, 0.20), (float("inf"), 0.30)]

_TAX_PROMPT = """You are an Indian tax expert (FY2024-25). Given these calculations, provide:
1. Which regime is better and by how much
2. Missed deductions the user should claim
3. One actionable step to save more tax next year

Data:
{data}

Be specific with ₹ amounts. Mention exact section numbers (80C, 80D, etc.)."""


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}

    income = profile.get("monthly_income", 50000) * 12
    investments_80c = profile.get("investments_80c", 0)
    nps_80ccd = profile.get("nps_contribution", 0)
    health_premium = profile.get("health_insurance_premium", 0)
    hra = profile.get("hra", 0)
    home_loan_interest = profile.get("home_loan_interest", 0)
    rent_paid = profile.get("rent_paid", 0)
    city = profile.get("city", "").lower()

    # Old regime deductions
    deduction_80c = min(investments_80c, 150000)
    deduction_80ccd = min(nps_80ccd, 50000)
    deduction_80d = min(health_premium, 25000)
    if profile.get("age", 0) >= 60:
        deduction_80d = min(health_premium, 50000)
    # Parents 80D additional
    parents_premium = profile.get("parents_health_premium", 0)
    parents_deduction = min(parents_premium, 50000 if profile.get("parents_senior", False) else 25000)
    deduction_80d += parents_deduction

    # HRA: minimum of (actual HRA received, rent - 10% basic, 50%/40% of basic for metro/non-metro)
    basic_salary = income * 0.4  # assume basic is ~40% of gross
    metro_cities = ["mumbai", "delhi", "kolkata", "chennai", "bangalore", "bengaluru", "hyderabad"]
    hra_pct = 0.50 if city in metro_cities else 0.40
    if hra > 0 and rent_paid > 0:
        deduction_hra = min(
            hra,
            rent_paid - (0.10 * basic_salary),
            hra_pct * basic_salary,
        )
        deduction_hra = max(deduction_hra, 0)
    else:
        deduction_hra = 0

    deduction_24b = min(home_loan_interest, 200000)
    standard_deduction_old = 50000

    total_deductions_old = (
        deduction_80c + deduction_80ccd + deduction_80d +
        deduction_hra + deduction_24b + standard_deduction_old
    )
    taxable_old = max(income - total_deductions_old, 0)
    tax_old = _compute_tax(taxable_old, _OLD_SLABS)

    # Old regime rebate: if taxable <= 5L, full rebate
    if taxable_old <= 500000:
        tax_old = 0

    # New regime
    standard_deduction_new = 75000
    taxable_new = max(income - standard_deduction_new, 0)
    tax_new = _compute_tax(taxable_new, _NEW_SLABS)

    # New regime rebate: if taxable <= 7L, full rebate
    if taxable_new <= 700000:
        tax_new = 0

    # Add 4% cess
    tax_old_total = round(tax_old * 1.04)
    tax_new_total = round(tax_new * 1.04)

    better_regime = "old" if tax_old_total < tax_new_total else "new"
    savings = abs(tax_old_total - tax_new_total)

    # Missed deductions
    missed = []
    if investments_80c < 150000:
        missed.append({"section": "80C", "unused": 150000 - investments_80c,
                        "suggestion": "ELSS mutual funds, PPF, or EPF VPF"})
    if nps_80ccd < 50000:
        missed.append({"section": "80CCD(1B)", "unused": 50000 - nps_80ccd,
                        "suggestion": "Additional NPS contribution"})
    if health_premium == 0:
        missed.append({"section": "80D", "unused": 25000,
                        "suggestion": "Health insurance premium (₹25K for self, ₹50K if parents)"})

    data = {
        "gross_income": income,
        "old_regime": {
            "deductions": {
                "80C": deduction_80c, "80CCD(1B)": deduction_80ccd,
                "80D": deduction_80d, "HRA": deduction_hra,
                "24(b)": deduction_24b, "standard": standard_deduction_old,
            },
            "total_deductions": total_deductions_old,
            "taxable_income": taxable_old,
            "tax": tax_old_total,
        },
        "new_regime": {
            "standard_deduction": standard_deduction_new,
            "taxable_income": taxable_new,
            "tax": tax_new_total,
        },
        "better_regime": better_regime,
        "savings": savings,
        "missed_deductions": missed,
    }

    try:
        result = await primary_llm.ainvoke(_TAX_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_tax_wizard(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "tax analysis", "intent": "tax_wizard",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "tax_wizard", "tax analysis", language, voice_mode)
    return {"analysis": output, "response": response}


def _compute_tax(taxable: float, slabs: list[tuple[float, float]]) -> float:
    tax = 0
    prev = 0
    for limit, rate in slabs:
        if taxable <= prev:
            break
        bracket = min(taxable, limit) - prev
        tax += bracket * rate
        prev = limit
    return tax
