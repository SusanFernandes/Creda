"""
Portfolio router — CAMS PDF upload, X-ray analysis, fund details.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Portfolio, PortfolioFund

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
