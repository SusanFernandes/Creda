"""
Tax Copilot agent — year-round tax optimization, tax-loss harvesting, continuous monitoring.
Uses versioned tax_config for all slab/limit references.
"""
import logging
from datetime import datetime
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState
from app.tax_config import get_tax_rules, compute_tax

logger = logging.getLogger("creda.agents.tax_copilot")

_TAX_COPILOT_PROMPT = """You are CREDA's Tax Copilot — a proactive year-round tax optimizer for Indian investors.
Current month: {month} of FY{fy}

User profile:
{profile}

Portfolio summary:
{portfolio}

Analyze and provide:
1. Current tax position estimate (projected tax liability this FY)
2. Tax-loss harvesting opportunities (suggest funds to book losses now to offset gains)
3. Month-specific action items (what should they do THIS month)
4. Deduction utilization tracker (how much of 80C/80D/80CCD they've used vs. limit)
5. One proactive move to save tax before {next_deadline}

Be specific with ₹ amounts and fund names. Reference exact tax sections."""


def _current_fy() -> str:
    """Return current financial year string like '2025-26'."""
    now = datetime.now()
    fy_start = now.year if now.month >= 4 else now.year - 1
    return f"{fy_start}-{(fy_start + 1) % 100:02d}"


def _months_left_in_fy() -> int:
    now = datetime.now()
    fy_end_month = 3  # March
    if now.month <= 3:
        return 3 - now.month + 1
    return 12 - now.month + 3 + 1


def _next_tax_deadline() -> str:
    now = datetime.now()
    deadlines = [
        (6, 15, "Advance tax Q1 (June 15)"),
        (9, 15, "Advance tax Q2 (Sep 15)"),
        (12, 15, "Advance tax Q3 (Dec 15)"),
        (3, 15, "Advance tax Q4 (Mar 15)"),
        (3, 31, "FY-end investment deadline (Mar 31)"),
        (7, 31, "ITR filing deadline (Jul 31)"),
    ]
    for month, day, label in deadlines:
        from datetime import date
        deadline_date = date(now.year if month >= now.month else now.year + 1, month, day)
        if deadline_date >= now.date():
            return label
    return "Mar 31 (FY-end)"


def _compute_advance_tax(gross_income: float, sec80c: float, nps: float, health: float) -> dict:
    """Compute quarterly advance tax schedule using versioned config."""
    rules = get_tax_rules()
    dl = rules.deductions
    std_ded = rules.old_regime.standard_deduction
    total_deductions = min(sec80c, dl.sec_80c) + min(nps, dl.sec_80ccd_1b) + min(health, dl.sec_80d_self) + std_ded
    taxable = max(gross_income - total_deductions, 0)

    tax = compute_tax(taxable, rules.old_regime, gross_income)

    return {
        "estimated_annual_tax": tax,
        "schedule": [
            {"quarter": "Q1 (by June 15)", "pct": "15%", "amount": round(tax * 0.15)},
            {"quarter": "Q2 (by Sep 15)", "pct": "45%", "amount": round(tax * 0.45) - round(tax * 0.15)},
            {"quarter": "Q3 (by Dec 15)", "pct": "75%", "amount": round(tax * 0.75) - round(tax * 0.45)},
            {"quarter": "Q4 (by Mar 15)", "pct": "100%", "amount": tax - round(tax * 0.75)},
        ],
    }


def _salary_restructuring_suggestions(profile: dict) -> list[dict]:
    """Suggest salary restructuring optimizations."""
    suggestions = []
    income = profile.get("monthly_income", 0) * 12
    hra = profile.get("hra", 0) * 12

    if income > 0:
        basic_pct = 0.50  # assume 50% basic
        ideal_basic = income * 0.40  # lowering basic reduces tax

        if hra == 0 and income > 600000:
            suggestions.append({
                "title": "Add HRA component",
                "description": f"If you're paying rent, restructure salary to include HRA. "
                              f"At 50% basic (₹{income * 0.5 / 12:,.0f}/month), HRA exemption could save ₹20,000-60,000/year.",
                "potential_saving": 40000,
            })

        nps_employer = profile.get("nps_contribution", 0)
        if nps_employer == 0 and income > 800000:
            suggestions.append({
                "title": "Request employer NPS (80CCD2)",
                "description": f"Employer NPS up to 14% of basic is tax-free under 80CCD(2). "
                              f"At 10% of basic: ₹{income * 0.5 * 0.10:,.0f}/year deduction, saving ₹{income * 0.5 * 0.10 * 0.30:,.0f} in tax.",
                "potential_saving": round(income * 0.5 * 0.10 * 0.30),
            })

        if income > 1000000:
            suggestions.append({
                "title": "Optimize basic salary ratio",
                "description": f"Consider 40% basic instead of 50%. Lower basic reduces EPF + PF liability. "
                              f"Balance with special allowance (fully taxable but flexible).",
                "potential_saving": round(income * 0.10 * 0.12),  # EPF savings
            })

    return suggestions


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    income = profile.get("monthly_income", 50000) * 12
    investments_80c = profile.get("investments_80c", 0)
    nps_80ccd = profile.get("nps_contribution", 0)
    health_premium = profile.get("health_insurance_premium", 0)

    # Deduction utilization
    deduction_tracker = {
        "80C": {"used": min(investments_80c, 150000), "limit": 150000, "remaining": max(150000 - investments_80c, 0)},
        "80CCD(1B)": {"used": min(nps_80ccd, 50000), "limit": 50000, "remaining": max(50000 - nps_80ccd, 0)},
        "80D": {"used": min(health_premium, 25000), "limit": 25000, "remaining": max(25000 - health_premium, 0)},
    }
    total_remaining = sum(d["remaining"] for d in deduction_tracker.values())

    # Tax-loss harvesting analysis
    funds = portfolio.get("funds", [])
    loss_funds = [f for f in funds if f.get("current_value", 0) < f.get("invested", 0)]
    gain_funds = [f for f in funds if f.get("current_value", 0) > f.get("invested", 0)]

    total_unrealized_gains = sum(f.get("current_value", 0) - f.get("invested", 0) for f in gain_funds)
    total_unrealized_losses = sum(f.get("invested", 0) - f.get("current_value", 0) for f in loss_funds)

    harvest_opportunities = []
    for f in loss_funds:
        loss = f.get("invested", 0) - f.get("current_value", 0)
        if loss > 1000:
            harvest_opportunities.append({
                "fund": f.get("fund_name", "Unknown"),
                "invested": f.get("invested", 0),
                "current": f.get("current_value", 0),
                "loss": loss,
                "action": "Redeem to book loss, reinvest in similar index fund after 30 days",
            })

    fy = _current_fy()
    months_left = _months_left_in_fy()
    next_deadline = _next_tax_deadline()

    data = {
        "financial_year": fy,
        "months_remaining": months_left,
        "next_deadline": next_deadline,
        "gross_income": income,
        "deduction_tracker": deduction_tracker,
        "total_deductions_remaining": total_remaining,
        "potential_tax_saving": round(total_remaining * 0.30),  # max 30% bracket
        "harvest_opportunities": harvest_opportunities[:3],
        "unrealized_gains": total_unrealized_gains,
        "unrealized_losses": total_unrealized_losses,
        "net_taxable_gains": max(total_unrealized_gains - total_unrealized_losses, 0),
        # Advance tax schedule
        "advance_tax": _compute_advance_tax(income, investments_80c, nps_80ccd, health_premium),
        # Salary restructuring suggestions
        "salary_restructuring": _salary_restructuring_suggestions(profile),
    }

    try:
        result = await primary_llm.ainvoke(_TAX_COPILOT_PROMPT.format(
            month=datetime.now().strftime("%B"),
            fy=fy,
            profile=str({k: profile.get(k) for k in ["monthly_income", "age", "investments_80c", "nps_contribution",
                                                       "health_insurance_premium", "risk_appetite"]}),
            portfolio=str({"funds_count": len(funds), "unrealized_gains": total_unrealized_gains,
                          "unrealized_losses": total_unrealized_losses}),
            next_deadline=next_deadline,
        ))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_tax_copilot(profile, portfolio_funds, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    funds_data = []
    if portfolio_funds:
        funds_data = [{c.name: getattr(f, c.name) for c in type(f).__table__.columns} for f in portfolio_funds]
    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": "tax copilot analysis",
        "intent": "tax_copilot",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
        "portfolio_data": {"funds": funds_data},
    }
    output = await run(state)
    response = await synthesize(output, "tax_copilot", "tax optimization", language, voice_mode)
    return {"analysis": output, "response": response}
