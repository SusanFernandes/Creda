"""Profile router — upsert, get, onboarding status."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import UserProfile

router = APIRouter()


class ProfileUpsertRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    language: Optional[str] = None
    monthly_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    savings: Optional[float] = None
    risk_appetite: Optional[str] = None
    employment_type: Optional[str] = None
    dependents: Optional[int] = None
    has_health_insurance: Optional[bool] = None
    life_insurance_cover: Optional[float] = None
    has_home_loan: Optional[bool] = None
    home_loan_outstanding: Optional[float] = None
    monthly_emi: Optional[float] = None
    emergency_fund: Optional[float] = None
    epf_balance: Optional[float] = None
    nps_balance: Optional[float] = None
    ppf_balance: Optional[float] = None
    investments_80c: Optional[float] = None
    nps_contribution: Optional[float] = None
    health_insurance_premium: Optional[float] = None
    hra: Optional[float] = None
    home_loan_interest: Optional[float] = None
    fire_target_age: Optional[int] = None
    fire_corpus_target: Optional[float] = None
    onboarding_complete: Optional[bool] = None


@router.post("/upsert")
async def upsert_profile(
    req: ProfileUpsertRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == auth.user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=auth.user_id)
        db.add(profile)

    # Update only provided fields
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return _serialize(profile)


@router.get("/{user_id}")
async def get_profile(
    user_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    return _serialize(profile)


@router.get("/{user_id}/is-onboarded")
async def is_onboarded(
    user_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    return {"onboarded": bool(profile and profile.onboarding_complete)}


def _serialize(p: UserProfile) -> dict[str, Any]:
    d: dict[str, Any] = {c.name: getattr(p, c.name) for c in UserProfile.__table__.columns}
    income = float(d.get("monthly_income") or 0)
    expenses = float(d.get("monthly_expenses") or 0)
    d["monthly_surplus"] = income - expenses
    return d
