"""
Nudges router — proactive financial notifications.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Nudge, UserProfile, Portfolio, PortfolioFund, GoalPlan

router = APIRouter()


@router.post("/generate")
async def generate_nudges(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Dynamically generate nudges based on user's current financial state.
    Idempotent — only generates if user has 0 pending nudges."""
    # Check if user already has unread nudges
    count_q = await db.execute(
        select(func.count()).select_from(Nudge).where(
            Nudge.user_id == auth.user_id, Nudge.is_read == False
        )
    )
    if count_q.scalar() > 0:
        return {"status": "already_has_nudges", "generated": 0}

    # Fetch profile
    prof_q = await db.execute(
        select(UserProfile).where(UserProfile.user_id == auth.user_id)
    )
    profile = prof_q.scalar_one_or_none()
    if not profile:
        return {"status": "no_profile", "generated": 0}

    # Fetch portfolio
    port_q = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id)
        .order_by(Portfolio.created_at.desc())
    )
    portfolio = port_q.scalar_one_or_none()

    funds = []
    if portfolio:
        funds_q = await db.execute(
            select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        funds = list(funds_q.scalars().all())

    # Fetch goals
    goals_q = await db.execute(
        select(GoalPlan).where(GoalPlan.user_id == auth.user_id)
    )
    goals = list(goals_q.scalars().all())

    now = datetime.now(timezone.utc)
    nudges_to_create = []

    # ── Rule 1: Emergency fund critically low ──
    monthly_exp = profile.monthly_expenses or 0
    emergency = profile.emergency_fund or 0
    target_emergency = monthly_exp * 6
    if target_emergency > 0 and emergency < target_emergency * 0.5:
        pct = round(emergency / target_emergency * 100, 1) if target_emergency else 0
        nudges_to_create.append(Nudge(
            user_id=auth.user_id,
            nudge_type="emergency_alert",
            title=f"🚨 Emergency Fund: Only {pct}% of Target",
            body=f"Your emergency fund covers only ₹{emergency:,.0f} of your ₹{target_emergency:,.0f} target (6 months expenses). One medical emergency and you're liquidating SIPs.",
            channel="app", sent_at=now,
        ))

    # ── Rule 2: 80C unused ──
    inv_80c = profile.investments_80c or 0
    remaining_80c = 150000 - inv_80c
    if remaining_80c > 30000:
        slab_rate = 0.312 if (profile.monthly_income or 0) * 12 > 1000000 else 0.208
        tax_saved = round(remaining_80c * slab_rate)
        nudges_to_create.append(Nudge(
            user_id=auth.user_id,
            nudge_type="tax_deadline",
            title=f"💡 Tax Season: ₹{remaining_80c/100000:.2f}L of 80C Unused",
            body=f"You've invested only ₹{inv_80c:,.0f} of the ₹1,50,000 80C limit. Save up to ₹{tax_saved:,.0f} in taxes by investing before March 31.",
            channel="app", sent_at=now,
        ))

    # ── Rule 3: No term life insurance ──
    if (profile.life_insurance_cover or 0) == 0:
        nudges_to_create.append(Nudge(
            user_id=auth.user_id,
            nudge_type="insurance_alert",
            title="No Term Life Insurance",
            body=f"You have zero life insurance cover. At age {profile.age or 29}, get at least ₹1 crore term plan. Premium: ~₹800/month.",
            channel="app", sent_at=now,
        ))

    # ── Rule 4: Portfolio overlap (3+ funds in same category) ──
    if funds:
        cat_counts = {}
        for f in funds:
            cat = f.category or "unknown"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, cnt in cat_counts.items():
            if cnt >= 3:
                cat_label = cat.replace("_", " ").title()
                cat_funds = [f for f in funds if f.category == cat]
                weakest = min(cat_funds, key=lambda x: x.xirr or 0)
                nudges_to_create.append(Nudge(
                    user_id=auth.user_id,
                    nudge_type="rebalance_alert",
                    title=f"Portfolio Overlap: {cnt} {cat_label} Funds",
                    body=f"You hold {cnt} {cat_label.lower()} funds with significant overlap. Weakest: {weakest.fund_name.split(' - ')[0]} ({weakest.xirr}% XIRR). Consider consolidating.",
                    channel="app", sent_at=now,
                ))

    # ── Rule 5: SIP reminder for any fund with regular investment ──
    if funds:
        top_fund = max(funds, key=lambda x: x.invested or 0)
        nudges_to_create.append(Nudge(
            user_id=auth.user_id,
            nudge_type="sip_reminder",
            title="⚠️ SIP Due Soon",
            body=f"Your monthly SIP in {top_fund.fund_name.split(' - ')[0]} is scheduled soon. Ensure sufficient balance in your bank account.",
            channel="app", sent_at=now,
        ))

    # ── Rule 6: Goal off-track ──
    for g in goals:
        if not g.is_on_track and g.target_amount and g.current_saved is not None:
            pct = round(g.current_saved / g.target_amount * 100, 1) if g.target_amount else 0
            nudges_to_create.append(Nudge(
                user_id=auth.user_id,
                nudge_type="goal_drift",
                title=f"📊 {g.goal_name}: {pct}% Progress",
                body=f"Your '{g.goal_name}' goal is off track. Target: ₹{g.target_amount:,.0f}, saved: ₹{g.current_saved:,.0f}.",
                channel="app", sent_at=now,
            ))
            break  # Only one goal nudge to avoid spam

    for nudge in nudges_to_create:
        db.add(nudge)
    await db.commit()

    return {"status": "ok", "generated": len(nudges_to_create)}


@router.get("/pending")
async def get_pending_nudges(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Nudge)
        .where(Nudge.user_id == auth.user_id, Nudge.is_read == False)
        .order_by(Nudge.sent_at.desc())
        .limit(20)
    )
    nudges = result.scalars().all()
    return [
        {
            "id": n.id,
            "nudge_type": n.nudge_type,
            "title": n.title,
            "body": n.body,
            "channel": n.channel,
            "action_url": n.action_url,
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
        }
        for n in nudges
    ]


@router.post("/{nudge_id}/read")
async def mark_read(
    nudge_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Nudge).where(Nudge.id == nudge_id, Nudge.user_id == auth.user_id)
    )
    nudge = result.scalar_one_or_none()
    if not nudge:
        raise HTTPException(404, "Nudge not found")
    nudge.is_read = True
    await db.commit()
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Nudge)
        .where(Nudge.user_id == auth.user_id, Nudge.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}
