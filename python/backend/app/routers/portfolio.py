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
from app.models import Portfolio, PortfolioFund, GoalPlan

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
        )
        db.add(fund)

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


# ═══════════════════════════════════════════════════════════════════════════
#  PORTFOLIO OPTIMIZATION & REBALANCING  (ported from Creda_Fastapi)
# ═══════════════════════════════════════════════════════════════════════════

class OptimizeRequest(BaseModel):
    goals: list[str] = []
    time_horizon_years: int = 25
    language: str = "en"


class RebalanceRequest(BaseModel):
    target_allocation: dict[str, float] = {}
    threshold: float = 0.05
    language: str = "en"


class SIPRequest(BaseModel):
    monthly_amount: float = 10000
    years: int = 15
    expected_return: float = 12.0
    step_up_percent: float = 10.0


@router.post("/optimize")
async def optimize_portfolio(
    body: OptimizeRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered portfolio optimization with specific fund recommendations."""
    from app.models import UserProfile

    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalar_one_or_none()

    funds_data: list[dict] = []
    total_value = 0.0
    if portfolio:
        funds_result = await db.execute(
            select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        funds = funds_result.scalars().all()
        total_value = sum(f.current_value or 0 for f in funds)
        funds_data = [
            {
                "fund_name": f.fund_name, "category": f.category,
                "invested": f.invested, "current_value": f.current_value,
                "xirr": f.xirr, "expense_ratio": f.expense_ratio,
            }
            for f in funds
        ]

    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == auth.user_id))
    profile = profile_result.scalar_one_or_none()

    goals_text = ", ".join(body.goals) if body.goals else "wealth creation, retirement"
    age = profile.age if profile else 30
    risk = profile.risk_tolerance if profile else "moderate"
    income = float(profile.monthly_income or 0) if profile else 0

    from app.core.llm import invoke_llm, fast_llm, clip_prompt
    prompt = (
        f"You are a SEBI-registered mutual fund advisor. Optimise this investor's portfolio.\n"
        f"Investor: Age {age}, Monthly income ₹{income:,.0f}, Risk tolerance: {risk}\n"
        f"Goals: {goals_text}\n"
        f"Time horizon: {body.time_horizon_years} years\n"
        f"Current portfolio value: ₹{total_value:,.0f}\n"
        f"Holdings:\n"
        + "\n".join(
            f"  - {f['fund_name']} ({f['category']}): ₹{f['current_value']:,.0f} | XIRR {f['xirr']}% | TER {f['expense_ratio']}%"
            for f in funds_data[:15]
        )
        + "\n\nProvide:\n1. Recommended target allocation percentages by category\n"
        "2. 3 specific actionable recommendations\n3. Expected return range\n"
        "Format as a clear, structured analysis."
    )
    try:
        llm_result = await invoke_llm(fast_llm, clip_prompt(prompt, 6000))
        optimization = llm_result.content.strip()
    except Exception:
        optimization = "Optimisation service temporarily unavailable. Ensure diversified allocation per age and risk tolerance."

    return {
        "goals": body.goals or ["wealth creation", "retirement"],
        "time_horizon": body.time_horizon_years,
        "current_value": total_value,
        "funds_count": len(funds_data),
        "optimization": optimization,
    }


@router.post("/check-rebalance")
async def check_rebalance(
    body: RebalanceRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Check portfolio drift against target allocation and provide rebalancing plan."""
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

    total_value = sum(f.current_value or 0 for f in funds)
    if total_value <= 0:
        return {"needs_rebalancing": False, "message": "No fund values to analyse"}

    # Current allocation by category
    current_alloc: dict[str, float] = {}
    for f in funds:
        cat = f.category or "other"
        current_alloc[cat] = current_alloc.get(cat, 0) + (f.current_value or 0)
    current_pcts = {cat: val / total_value for cat, val in current_alloc.items()}

    target = body.target_allocation or current_pcts
    all_cats = set(list(current_pcts.keys()) + list(target.keys()))
    drift: dict[str, dict] = {}
    max_drift = 0.0
    for cat in all_cats:
        curr = current_pcts.get(cat, 0)
        tgt = target.get(cat, 0)
        d = abs(curr - tgt)
        drift[cat] = {"current": round(curr * 100, 1), "target": round(tgt * 100, 1), "drift": round(d * 100, 1)}
        max_drift = max(max_drift, d)

    needs_rebalancing = max_drift > body.threshold

    result_data: dict = {
        "needs_rebalancing": needs_rebalancing,
        "max_drift_pct": round(max_drift * 100, 1),
        "threshold_pct": round(body.threshold * 100, 1),
        "total_value": total_value,
        "allocation_drift": drift,
    }

    if needs_rebalancing:
        from app.core.llm import invoke_llm, fast_llm, clip_prompt
        drift_text = "\n".join(
            f"  {cat}: Current {d['current']}% | Target {d['target']}% | Drift {d['drift']}%"
            for cat, d in drift.items()
        )
        prompt = (
            f"You are a SEBI-registered mutual fund advisor. Portfolio rebalancing analysis:\n"
            f"Portfolio value: ₹{total_value:,.0f}\nDrift threshold: {body.threshold * 100:.0f}%\n"
            f"Allocation drift:\n{drift_text}\n\n"
            "Provide exactly 3 numbered rebalancing recommendations. Be specific with fund categories and amounts."
        )
        try:
            llm_result = await invoke_llm(fast_llm, clip_prompt(prompt, 4000))
            result_data["recommendations"] = llm_result.content.strip()
        except Exception:
            result_data["recommendations"] = "Review drift percentages above and rebalance overweight categories."

    return result_data


@router.post("/sip-calculator")
async def sip_calculator(body: SIPRequest):
    """Pure-math SIP calculator — no auth required, no LLM."""
    monthly = body.monthly_amount
    years = body.years
    annual_return = body.expected_return / 100
    step_up = body.step_up_percent / 100
    r = annual_return / 12
    n = years * 12

    # Basic SIP future value
    if r > 0 and n > 0:
        basic_fv = monthly * (((1 + r) ** n) - 1) / r * (1 + r)
    else:
        basic_fv = monthly * n
    total_invested = monthly * n

    # Step-up SIP future value
    step_up_fv = 0.0
    m = monthly
    for year in range(years):
        remaining = years - year
        year_fv = m * (((1 + r) ** 12) - 1) / r * (1 + r) if r > 0 else m * 12
        step_up_fv += year_fv * ((1 + annual_return) ** (remaining - 1))
        m *= (1 + step_up)

    return {
        "monthly_amount": monthly,
        "years": years,
        "expected_return": body.expected_return,
        "total_invested": round(total_invested),
        "expected_value": round(basic_fv),
        "wealth_gain": round(basic_fv - total_invested),
        "step_up_percent": body.step_up_percent,
        "step_up_corpus": round(step_up_fv),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Portfolio History / Net-worth Timeline
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/history/{user_id}")
async def portfolio_history(user_id: str, db: AsyncSession = Depends(get_db)):
    """Return portfolio value snapshots for net-worth timeline.

    Since we don't store daily snapshots yet, this returns:
    - The portfolio creation date + invested value as T0
    - The last update date + current value as T1
    - Per-fund breakdown with invested vs current
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    portfolio = result.scalars().first()
    if not portfolio:
        return {"snapshots": [], "funds_timeline": []}

    funds_result = await db.execute(
        select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
    )
    funds = funds_result.scalars().all()

    snapshots = [
        {
            "date": portfolio.created_at.isoformat() if portfolio.created_at else None,
            "total_invested": portfolio.total_invested or 0,
            "current_value": portfolio.total_invested or 0,
        },
        {
            "date": (portfolio.updated_at or portfolio.created_at).isoformat()
            if (portfolio.updated_at or portfolio.created_at)
            else None,
            "total_invested": portfolio.total_invested or 0,
            "current_value": portfolio.current_value or 0,
        },
    ]

    funds_timeline = [
        {
            "fund_name": f.fund_name,
            "category": f.category,
            "invested": f.invested or 0,
            "current_value": f.current_value or 0,
            "gain": round((f.current_value or 0) - (f.invested or 0), 2),
            "gain_pct": round(
                ((f.current_value or 0) / (f.invested or 1) - 1) * 100, 2
            ),
        }
        for f in funds
    ]

    return {
        "user_id": user_id,
        "portfolio_id": portfolio.id,
        "xirr": portfolio.xirr,
        "snapshots": snapshots,
        "funds_timeline": funds_timeline,
    }
