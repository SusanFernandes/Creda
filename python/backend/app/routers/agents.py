"""
Agent-specific endpoints — dedicated routes that skip intent routing entirely.
Each endpoint calls its agent directly without going through LangGraph.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import UserProfile

router = APIRouter()


class AgentRequest(BaseModel):
    language: str = "en"
    voice_mode: bool = False


class StressTestRequest(AgentRequest):
    events: list[str] = ["market_crash_30"]


class CouplesRequest(AgentRequest):
    partner_income: float = 0
    partner_expenses: float = 0
    split_strategy: str = "proportional"


class GoalSimulatorRequest(AgentRequest):
    target_amount: float = 5000000
    years: int = 10


class ResearchRequest(AgentRequest):
    message: str = ""


class LifeEventRequest(AgentRequest):
    message: str = ""


async def _get_profile(user_id: str, db: AsyncSession) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Complete onboarding first — profile not found")
    return profile


@router.post("/fire-planner")
async def fire_planner(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.fire_planner import run_fire_planner
    return await run_fire_planner(profile, body.language, body.voice_mode)


@router.post("/tax-wizard")
async def tax_wizard(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.tax_wizard import run_tax_wizard
    return await run_tax_wizard(profile, body.language, body.voice_mode)


@router.post("/money-health")
async def money_health(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.money_health import run_money_health
    return await run_money_health(profile, body.language, body.voice_mode)


@router.post("/stress-test")
async def stress_test(
    body: StressTestRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.stress_test import run_stress_test
    return await run_stress_test(profile, body.events, body.language, body.voice_mode)


@router.post("/budget-coach")
async def budget_coach(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.budget_coach import run_budget_coach
    return await run_budget_coach(profile, body.language, body.voice_mode)


@router.post("/goal-planner")
async def goal_planner(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.goal_planner import run_goal_planner
    return await run_goal_planner(profile, body.language, body.voice_mode)


@router.post("/couples-finance")
async def couples_finance(
    body: CouplesRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    partner_income = body.partner_income
    partner_expenses = body.partner_expenses

    # Auto-detect linked spouse if partner data not provided
    if partner_income == 0:
        from app.models import FamilyLink, UserProfile
        from sqlalchemy import or_
        link_result = await db.execute(
            select(FamilyLink).where(
                or_(FamilyLink.owner_id == auth.user_id, FamilyLink.member_id == auth.user_id),
                FamilyLink.is_accepted == True,
                FamilyLink.relationship_type == "spouse",
            )
        )
        link = link_result.scalar_one_or_none()
        if link:
            spouse_id = link.member_id if link.owner_id == auth.user_id else link.owner_id
            spouse_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == spouse_id)
            )
            spouse_profile = spouse_result.scalar_one_or_none()
            if spouse_profile:
                partner_income = spouse_profile.monthly_income or 0
                partner_expenses = spouse_profile.monthly_expenses or 0

    from app.agents.couples_finance import run_couples_finance
    return await run_couples_finance(
        profile, partner_income, partner_expenses,
        body.split_strategy, body.language, body.voice_mode,
    )


# ── ET-Inspired Agents ────────────────────────────────────────────────


@router.post("/market-pulse")
async def market_pulse(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    # Also try loading portfolio with funds
    from app.models import Portfolio, PortfolioFund
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = port_result.scalar_one_or_none()
    funds = []
    if portfolio:
        funds_result = await db.execute(select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id))
        funds = list(funds_result.scalars().all())
    from app.agents.market_pulse import run_market_pulse
    return await run_market_pulse(profile, portfolio, funds, body.language, body.voice_mode)


@router.post("/tax-copilot")
async def tax_copilot(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.models import Portfolio, PortfolioFund
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = port_result.scalar_one_or_none()
    funds = []
    if portfolio:
        funds_result = await db.execute(select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id))
        funds = funds_result.scalars().all()
    from app.agents.tax_copilot import run_tax_copilot
    return await run_tax_copilot(profile, funds, body.language, body.voice_mode)


@router.post("/money-personality")
async def money_personality(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.money_personality import run_money_personality
    return await run_money_personality(profile, body.language, body.voice_mode)


@router.post("/goal-simulator")
async def goal_simulator(
    body: GoalSimulatorRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.goal_simulator import run_goal_simulator
    return await run_goal_simulator(profile, body.language, body.voice_mode, body.target_amount, body.years)


@router.post("/social-proof")
async def social_proof(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.social_proof import run_social_proof
    return await run_social_proof(profile, body.language, body.voice_mode)


@router.post("/et-research")
async def et_research(
    body: ResearchRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.et_research import run_et_research
    return await run_et_research(body.message, profile, body.language, body.voice_mode)


@router.post("/human-handoff")
async def human_handoff(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.human_handoff import run as run_handoff
    from app.agents.state import FinancialState
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": auth.user_id, "message": "human handoff request",
        "intent": "human_handoff", "language": body.language,
        "voice_mode": body.voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    return await run_handoff(state)


@router.post("/family-wealth")
async def family_wealth(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.family_wealth import run as run_family
    from app.agents.state import FinancialState
    from app.models import Portfolio, PortfolioFund
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = port_result.scalar_one_or_none()
    portfolio_value = 0.0
    if portfolio:
        funds_result = await db.execute(
            select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        funds = funds_result.scalars().all()
        portfolio_value = sum(f.current_value or 0 for f in funds)
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": auth.user_id, "message": "family wealth view",
        "intent": "family_wealth", "language": body.language,
        "voice_mode": body.voice_mode, "history": [],
        "user_profile": profile_dict,
        "portfolio_data": {"current_value": portfolio_value},
        "db": db,
    }
    return await run_family(state)


@router.post("/expense-analytics")
async def expense_analytics(
    body: AgentRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.agents.expense_analytics import run_expense_analytics
    return await run_expense_analytics(profile, body.language, body.voice_mode)


@router.post("/life-event-advisor")
async def life_event_advisor(
    body: LifeEventRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(auth.user_id, db)
    from app.models import Portfolio, PortfolioFund, GoalPlan
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = port_result.scalar_one_or_none()
    goals_result = await db.execute(select(GoalPlan).where(GoalPlan.user_id == auth.user_id))
    goals_list = list(goals_result.scalars().all())
    from app.agents.life_event_advisor import run_life_event_advisor
    return await run_life_event_advisor(
        profile, portfolio, goals_list, body.message, body.language, body.voice_mode
    )
