"""GET/PATCH user return assumptions + stress scenarios JSON."""

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.core.assumptions import ensure_user_assumptions_row
from app.database import get_db

router = APIRouter()


class AssumptionsPatch(BaseModel):
    inflation_rate: Optional[float] = None
    equity_lc_return: Optional[float] = None
    equity_mc_return: Optional[float] = None
    equity_sc_return: Optional[float] = None
    debt_return: Optional[float] = None
    sip_stepup_pct: Optional[float] = None
    stress_scenarios: Optional[dict[str, Any]] = None


@router.get("")
async def get_assumptions(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await ensure_user_assumptions_row(db, auth.user_id)
    await db.commit()
    await db.refresh(row)
    return {
        "inflation_rate": row.inflation_rate,
        "equity_lc_return": row.equity_lc_return,
        "equity_mc_return": row.equity_mc_return,
        "equity_sc_return": row.equity_sc_return,
        "debt_return": row.debt_return,
        "sip_stepup_pct": row.sip_stepup_pct,
        "stress_scenarios": row.stress_scenarios or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.patch("")
async def patch_assumptions(
    body: AssumptionsPatch,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await ensure_user_assumptions_row(db, auth.user_id)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(row, field, val)
    await db.commit()
    await db.refresh(row)
    return {
        "inflation_rate": row.inflation_rate,
        "equity_lc_return": row.equity_lc_return,
        "equity_mc_return": row.equity_mc_return,
        "equity_sc_return": row.equity_sc_return,
        "debt_return": row.debt_return,
        "sip_stepup_pct": row.sip_stepup_pct,
        "stress_scenarios": row.stress_scenarios or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
