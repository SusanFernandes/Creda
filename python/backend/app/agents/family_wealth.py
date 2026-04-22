"""
Family Wealth agent — household-level financial aggregation.
"Your family's combined net worth is ₹1.2Cr — here's how to optimize across members."
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.family_wealth")

_FAMILY_PROMPT = """You are a household wealth advisor for Indian families.
Given the family members' combined financial data, provide:
1. Total household net worth and breakdown by member
2. Insurance coverage gaps across the family
3. Tax optimization across family members (e.g., invest in lower-tax-bracket spouse)
4. One concrete action to improve the family's overall finances

Family data: {family_data}
Primary user profile: {user}

Use ₹ amounts. Be specific and actionable. Consider Indian tax rules for HUF, clubbing provisions, etc."""


async def _get_family_members(user_id: str, db: AsyncSession) -> list[dict]:
    """Fetch linked family members and their profiles/portfolios."""
    from app.models import FamilyLink, UserProfile, Portfolio, PortfolioFund

    result = await db.execute(
        select(FamilyLink).where(
            FamilyLink.owner_id == user_id,
            FamilyLink.is_accepted == True,
        )
    )
    links = result.scalars().all()

    members = []
    for link in links:
        # Get member profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == link.member_id)
        )
        member_profile = profile_result.scalar_one_or_none()
        if not member_profile:
            continue

        # Get member portfolio via Portfolio → PortfolioFund
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == link.member_id)
        )
        member_portfolio = portfolio_result.scalar_one_or_none()

        portfolio_value = 0
        holdings_count = 0
        if member_portfolio:
            funds_result = await db.execute(
                select(PortfolioFund).where(PortfolioFund.portfolio_id == member_portfolio.id)
            )
            funds = funds_result.scalars().all()
            portfolio_value = sum(f.current_value or 0 for f in funds)
            holdings_count = len(funds)

        members.append({
            "relationship": link.relationship_type,
            "age": member_profile.age,
            "income": member_profile.monthly_income or 0,
            "expenses": member_profile.monthly_expenses or 0,
            "emergency_fund": member_profile.emergency_fund or 0,
            "risk_appetite": member_profile.risk_appetite or "moderate",
            "has_health_insurance": member_profile.has_health_insurance,
            "portfolio_value": portfolio_value,
            "holdings_count": holdings_count,
        })

    return members


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}

    user_income = profile.get("monthly_income", 0)
    user_portfolio = portfolio.get("current_value", 0)
    user_emergency = profile.get("emergency_fund", 0)

    # Build primary user data
    primary = {
        "role": "primary",
        "age": profile.get("age", 30),
        "income": user_income,
        "expenses": profile.get("monthly_expenses", 0),
        "emergency_fund": user_emergency,
        "portfolio_value": user_portfolio,
        "has_insurance": profile.get("has_health_insurance", False),
    }

    # Get family members if db is available
    # Get family members from DB
    family_members = []
    try:
        from app.database import AsyncSessionLocal
        user_id = state.get("user_id", "")
        async with AsyncSessionLocal() as db_session:
            family_members = await _get_family_members(user_id, db_session)
    except Exception as e:
        logger.warning("Could not fetch family members: %s", e)

    all_members = [primary] + family_members

    # Aggregate household metrics
    total_income = sum(m.get("income", 0) for m in all_members)
    total_portfolio = sum(m.get("portfolio_value", 0) for m in all_members)
    total_emergency = primary["emergency_fund"] + sum(
        m.get("emergency_fund", 0) for m in family_members
    )
    total_expenses = sum(m.get("expenses", 0) for m in all_members)
    insured_count = sum(
        1 for m in all_members if m.get("has_insurance") or m.get("has_health_insurance")
    )
    total_count = len(all_members)

    household = {
        "total_members": total_count,
        "total_monthly_income": total_income,
        "total_portfolio_value": total_portfolio,
        "total_emergency_fund": total_emergency,
        "household_net_worth": total_portfolio + total_emergency,
        "insurance_coverage": f"{insured_count}/{total_count} members insured",
        "household_savings_rate": round(
            (total_income - total_expenses) / total_income * 100, 1
        ) if total_income > 0 else 0,
    }

    # Optimization suggestions
    suggestions = []
    if total_count > 1:
        incomes = sorted(
            [(m.get("role", m.get("relationship", "")), m.get("income", 0)) for m in all_members],
            key=lambda x: x[1],
        )
        if len(incomes) >= 2 and incomes[0][1] < incomes[-1][1]:
            suggestions.append({
                "type": "tax_optimization",
                "tip": f"Invest in {incomes[0][0]}'s name for lower tax bracket. "
                       f"Potential saving: ₹{(incomes[-1][1] - incomes[0][1]) * 0.1 * 12:,.0f}/year.",
            })

    if insured_count < total_count:
        suggestions.append({
            "type": "insurance_gap",
            "tip": f"{total_count - insured_count} family member(s) lack health insurance. "
                   f"Family floater for ₹10L-20L costs ₹15,000-25,000/year.",
        })

    if total_emergency < total_expenses * 6:
        gap = total_expenses * 6 - total_emergency
        suggestions.append({
            "type": "emergency_fund",
            "tip": f"Household emergency fund is ₹{gap:,.0f} short of 6-month target.",
        })

    # LLM analysis
    family_data = {"household": household, "members": all_members, "suggestions": suggestions}
    prompt = _FAMILY_PROMPT.format(family_data=family_data, user=profile)

    try:
        llm_response = await primary_llm(prompt)
        analysis = llm_response
    except Exception as e:
        logger.error("Family wealth LLM failed: %s", e)
        analysis = "Unable to generate family wealth analysis at this time."

    return {
        "agent": "family_wealth",
        "data": {
            "household": household,
            "members": [
                {"role": m.get("role", m.get("relationship", "member")),
                 "income": m.get("income", 0),
                 "portfolio": m.get("portfolio_value", 0)}
                for m in all_members
            ],
            "suggestions": suggestions,
            "analysis": analysis,
        },
    }
