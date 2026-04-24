"""Fund overlap from `fund_holdings` (common stock/bond ISINs between two funds)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FundHolding


async def get_latest_holdings_month(db: AsyncSession) -> date | None:
    r = await db.execute(select(func.max(FundHolding.month)))
    m = r.scalar()
    return m


async def get_holdings(db: AsyncSession, isin: str, month: date | None) -> dict[str, float]:
    """Map holding_isin -> weight (decimal, e.g. 0.08 = 8%)."""
    if not isin or not month:
        return {}
    r = await db.execute(
        select(FundHolding).where(
            FundHolding.fund_isin == isin,
            FundHolding.month == month,
        )
    )
    rows = r.scalars().all()
    return {
        row.holding_isin: float(row.weight or 0)
        for row in rows
        if row.holding_isin
    }


async def compute_overlap(user_fund_isins: list[str], db: AsyncSession) -> list[dict[str, Any]]:
    """
    For each pair of funds in the portfolio, common holdings where both weights > 2%.
    """
    overlaps: list[dict[str, Any]] = []
    month = await get_latest_holdings_month(db)
    if not month:
        return overlaps
    cleaned = [x for x in user_fund_isins if x]
    for i, isin_a in enumerate(cleaned):
        holdings_a = await get_holdings(db, isin_a, month)
        for isin_b in cleaned[i + 1 :]:
            holdings_b = await get_holdings(db, isin_b, month)
            common = set(holdings_a.keys()) & set(holdings_b.keys())
            for h_isin in common:
                wa = holdings_a[h_isin]
                wb = holdings_b[h_isin]
                if wa > 0.02 and wb > 0.02:
                    overlaps.append(
                        {
                            "fund_a": isin_a,
                            "fund_b": isin_b,
                            "holding_isin": h_isin,
                            "weight_a": wa,
                            "weight_b": wb,
                        }
                    )
    return overlaps


async def fetch_holding_name(db: AsyncSession, holding_isin: str, month: date | None) -> str:
    if not holding_isin or not month:
        return ""
    r = await db.execute(
        select(FundHolding.holding_name)
        .where(
            FundHolding.holding_isin == holding_isin,
            FundHolding.month == month,
        )
        .limit(1)
    )
    row = r.first()
    return str(row[0]) if row and row[0] else ""
