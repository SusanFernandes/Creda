"""
Portfolio router — CAMS PDF upload, X-ray analysis, fund details.
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import GoalPlan, Portfolio, PortfolioFund, UserProfile

router = APIRouter()


@router.post("/upload")
async def upload_cams(
    file: UploadFile = File(...),
    password: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Parse CAMS/KFintech PDF → populate portfolio + funds."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "File too large (max 10MB)")

    from app.agents.portfolio_xray import parse_cams_statement
    parsed = await parse_cams_statement(pdf_bytes, password)

    # Upsert portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=auth.user_id)
        db.add(portfolio)

    portfolio.total_invested = parsed["total_invested"]
    portfolio.current_value = parsed["current_value"]
    portfolio.xirr = parsed.get("xirr", 0)
    from datetime import datetime
    portfolio.parsed_at = datetime.utcnow()

    await db.flush()

    # Replace old funds with new parsed ones
    await db.execute(
        PortfolioFund.__table__.delete().where(PortfolioFund.portfolio_id == portfolio.id)
    )
    for fund_data in parsed.get("funds", []):
        fund = PortfolioFund(
            portfolio_id=portfolio.id,
            fund_name=fund_data.get("fund_name", ""),
            amc=fund_data.get("amc", ""),
            scheme_type=fund_data.get("scheme_type", ""),
            category=fund_data.get("category", ""),
            plan_type=fund_data.get("plan_type", ""),
            invested=fund_data.get("invested", 0),
            current_value=fund_data.get("current_value", 0),
            units=fund_data.get("units", 0),
            xirr=fund_data.get("xirr", 0),
            expense_ratio=fund_data.get("expense_ratio", 0),
            isin=fund_data.get("isin") or "",
        )
        db.add(fund)

    prof_r = await db.execute(select(UserProfile).where(UserProfile.user_id == auth.user_id))
    uprof = prof_r.scalar_one_or_none()
    if uprof:
        uprof.cams_uploaded = True

    await db.commit()
    await db.refresh(portfolio)

    return {
        "portfolio_id": portfolio.id,
        "total_invested": portfolio.total_invested,
        "current_value": portfolio.current_value,
        "xirr": portfolio.xirr,
        "funds_count": len(parsed.get("funds", [])),
    }


@router.post("/xray")
async def portfolio_xray(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Run full X-ray analysis on latest portfolio."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "No portfolio found. Upload a CAMS statement first.")

    # Load funds
    funds_result = await db.execute(
        select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
    )
    funds = funds_result.scalars().all()

    from app.agents.portfolio_xray import run_xray_analysis
    analysis = await run_xray_analysis(
        portfolio=portfolio,
        funds=funds,
        user_id=auth.user_id,
    )

    from datetime import datetime
    portfolio.last_xray_at = datetime.utcnow()
    await db.commit()

    return analysis


@router.get("/summary")
async def portfolio_summary(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get latest portfolio summary without running full X-ray."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "No portfolio found")

    funds_result = await db.execute(
        select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
    )
    funds = funds_result.scalars().all()

    return {
        "portfolio_id": portfolio.id,
        "total_invested": portfolio.total_invested,
        "current_value": portfolio.current_value,
        "xirr": portfolio.xirr,
        "gain": portfolio.current_value - portfolio.total_invested,
        "gain_pct": ((portfolio.current_value - portfolio.total_invested) / portfolio.total_invested * 100)
            if portfolio.total_invested > 0 else 0,
        "funds_count": len(funds),
        "parsed_at": portfolio.parsed_at.isoformat() if portfolio.parsed_at else None,
        "last_xray_at": portfolio.last_xray_at.isoformat() if portfolio.last_xray_at else None,
        "funds": [
            {
                "fund_name": f.fund_name,
                "amc": f.amc,
                "scheme_type": f.scheme_type,
                "category": f.category,
                "invested": f.invested,
                "current_value": f.current_value,
                "xirr": f.xirr,
                "expense_ratio": f.expense_ratio,
            }
            for f in funds
        ],
    }


@router.get("/nav/search")
async def nav_search(q: str = "", auth: AuthContext = Depends(get_auth)):
    """Search AMFI schemes by name — for autocomplete or fund lookup."""
    from app.services.amfi_nav import search_schemes
    results = await search_schemes(q, max_results=10)
    return {"results": results}


@router.get("/nav/stats")
async def nav_stats(auth: AuthContext = Depends(get_auth)):
    """Get AMFI NAV cache status."""
    from app.services.amfi_nav import get_cache_stats
    return get_cache_stats()


@router.post("/refresh-navs")
async def refresh_portfolio_navs(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Refresh all fund NAVs in user's portfolio using AMFI data."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "No portfolio found")

    funds_result = await db.execute(
        select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
    )
    funds = funds_result.scalars().all()

    from app.services.amfi_nav import get_fund_nav
    updated = 0
    for fund in funds:
        if not fund.units or fund.units <= 0:
            continue
        nav_data = await get_fund_nav(fund.fund_name)
        if nav_data and nav_data.get("nav"):
            fund.current_value = round(fund.units * nav_data["nav"], 2)
            updated += 1

    if updated:
        portfolio.current_value = sum(f.current_value or 0 for f in funds)
        from datetime import datetime
        portfolio.parsed_at = datetime.utcnow()
        await db.commit()

    return {
        "updated_funds": updated,
        "total_funds": len(funds),
        "new_total_value": portfolio.current_value,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  GOAL ↔ FUND LINKING
# ═══════════════════════════════════════════════════════════════════════════

class LinkFundsRequest(BaseModel):
    goal_id: str
    fund_ids: list[str]


class GoalCreateRequest(BaseModel):
    goal_name: str = Field(..., max_length=200)
    target_amount: float = Field(..., gt=0)
    target_date: Optional[str] = None  # YYYY-MM-DD
    current_saved: float = 0
    monthly_investment: float = 0


@router.post("/goals")
async def create_goal(
    body: GoalCreateRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a saved financial goal (shown in Goal Planner and life-event flows)."""
    td: Optional[date] = None
    if body.target_date:
        try:
            td = datetime.strptime(body.target_date[:10], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "target_date must be YYYY-MM-DD")

    goal = GoalPlan(
        user_id=auth.user_id,
        goal_name=body.goal_name.strip(),
        target_amount=body.target_amount,
        target_date=td,
        monthly_investment=body.monthly_investment,
        current_saved=body.current_saved or 0,
    )
    if goal.target_amount > 0:
        goal.progress_pct = min(100.0, round((goal.current_saved or 0) / goal.target_amount * 100, 1))
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return {
        "id": goal.id,
        "goal_name": goal.goal_name,
        "target_amount": goal.target_amount,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "current_saved": goal.current_saved,
    }


@router.get("/goals")
async def list_goals_with_funds(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """List user goals with linked fund details for the linking UI."""
    goals_result = await db.execute(
        select(GoalPlan).where(GoalPlan.user_id == auth.user_id)
    )
    goals = goals_result.scalars().all()

    # Also get the portfolio funds
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = port_result.scalar_one_or_none()
    funds = []
    if portfolio:
        funds_result = await db.execute(
            select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        funds = funds_result.scalars().all()

    return {
        "goals": [
            {
                "id": g.id,
                "goal_name": g.goal_name,
                "target_amount": g.target_amount,
                "linked_fund_ids": g.linked_fund_ids or [],
                "progress_pct": g.progress_pct,
                "is_on_track": g.is_on_track,
            }
            for g in goals
        ],
        "funds": [
            {
                "id": f.id,
                "fund_name": f.fund_name,
                "category": f.category,
                "current_value": f.current_value,
                "invested": f.invested,
            }
            for f in funds
        ],
    }


@router.post("/goals/link")
async def link_funds_to_goal(
    body: LinkFundsRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Link specific portfolio funds to a goal."""
    result = await db.execute(
        select(GoalPlan).where(GoalPlan.id == body.goal_id, GoalPlan.user_id == auth.user_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Goal not found")

    # Validate fund_ids belong to user
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = port_result.scalar_one_or_none()
    if portfolio:
        funds_result = await db.execute(
            select(PortfolioFund.id).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        valid_ids = {r[0] for r in funds_result.all()}
        body.fund_ids = [fid for fid in body.fund_ids if fid in valid_ids]

    goal.linked_fund_ids = body.fund_ids

    # Calculate linked value for progress tracking
    if portfolio and body.fund_ids:
        linked_result = await db.execute(
            select(PortfolioFund).where(PortfolioFund.id.in_(body.fund_ids))
        )
        linked_funds = linked_result.scalars().all()
        linked_value = sum(f.current_value or 0 for f in linked_funds)
        goal.current_saved = linked_value
        if goal.target_amount > 0:
            goal.progress_pct = min(100.0, round(linked_value / goal.target_amount * 100, 1))

    await db.commit()
    return {
        "goal_id": goal.id,
        "linked_fund_ids": goal.linked_fund_ids,
        "current_saved": goal.current_saved,
        "progress_pct": goal.progress_pct,
    }
