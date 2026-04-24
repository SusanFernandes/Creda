"""
Admin router — platform metrics, activity logs, user management.
Protected: requires authenticated user (in production, add admin role check).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import User, UserProfile, ActivityLog, ConversationMessage, Portfolio, AdviceLog, Nudge
from app.services.activity import get_recent_activity, get_activity_stats

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide statistics for admin dashboard."""
    stats = await get_activity_stats(db)

    # Additional metrics
    total_nudges = (await db.execute(select(func.count(Nudge.id)))).scalar() or 0
    unread_nudges = (await db.execute(
        select(func.count(Nudge.id)).where(Nudge.is_read == False)  # noqa: E712
    )).scalar() or 0

    stats["total_nudges"] = total_nudges
    stats["unread_nudges"] = unread_nudges

    return stats


@router.get("/activity")
async def admin_activity(
    user_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Recent activity logs with pagination."""
    from app.models import ActivityLog
    base_q = select(ActivityLog)
    if user_id:
        base_q = base_q.where(ActivityLog.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar() or 0
    items = await get_recent_activity(db, user_id=user_id, limit=limit, offset=offset)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/users")
async def admin_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """List users with basic stats and pagination."""
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    result = await db.execute(
        select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
    )
    users = []
    for user in result.scalars():
        # Get profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = profile_result.scalars().first()

        # Count messages
        msg_count = (await db.execute(
            select(func.count(ConversationMessage.id))
            .where(ConversationMessage.user_id == user.id)
        )).scalar() or 0

        users.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "onboarded": profile.onboarding_complete if profile else False,
            "language": profile.language if profile else "en",
            "message_count": msg_count,
        })

    return {"items": users, "total": total, "offset": offset, "limit": limit}
