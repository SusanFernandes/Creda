"""Load or create per-user financial assumptions (returns, inflation, stress JSON)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserAssumptions


_DEFAULT_ROW: dict[str, Any] = {
    "inflation_rate": 0.06,
    "equity_lc_return": 0.12,
    "equity_mc_return": 0.14,
    "equity_sc_return": 0.16,
    "debt_return": 0.07,
    "sip_stepup_pct": 0.10,
    "stress_scenarios": {},
}


async def get_user_assumptions(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Return assumptions dict. Uses DB row if present; otherwise in-memory defaults (no implicit insert)."""
    result = await db.execute(select(UserAssumptions).where(UserAssumptions.user_id == user_id))
    row = result.scalar_one_or_none()
    if not row:
        out = dict(_DEFAULT_ROW)
        out["stress_scenarios"] = dict(out.get("stress_scenarios") or {})
        return out
    out = {k: getattr(row, k) for k in _DEFAULT_ROW}
    if out.get("stress_scenarios") is None:
        out["stress_scenarios"] = {}
    return out


async def ensure_user_assumptions_row(db: AsyncSession, user_id: str) -> UserAssumptions:
    """Return ORM row for PATCH; creates and attaches row — caller must commit."""
    result = await db.execute(select(UserAssumptions).where(UserAssumptions.user_id == user_id))
    row = result.scalar_one_or_none()
    if not row:
        row = UserAssumptions(user_id=user_id, **_DEFAULT_ROW)
        db.add(row)
        await db.flush()
    return row
