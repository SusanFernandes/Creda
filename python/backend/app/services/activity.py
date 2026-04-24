"""
Activity logging service — records user actions for audit trail and admin dashboard.
"""
import logging
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog

logger = logging.getLogger("creda.activity")


async def log_activity(
    db: AsyncSession,
    user_id: str | None,
    action: str,
    detail: str = "",
    ip_address: str = "",
    user_agent: str = "",
    metadata: dict | None = None,
):
    """Record a user activity event."""
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
    db.add(entry)
    await db.commit()


async def get_recent_activity(
    db: AsyncSession,
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Get recent activity logs, optionally filtered by user, with pagination."""
    query = select(ActivityLog).order_by(desc(ActivityLog.created_at)).offset(offset).limit(limit)
    if user_id:
        query = query.where(ActivityLog.user_id == user_id)
    result = await db.execute(query)
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else "",
            "metadata": log.metadata_json,
        }
        for log in result.scalars()
    ]


async def get_activity_stats(db: AsyncSession) -> dict:
    """Get aggregated activity stats for admin dashboard."""
    from app.models import User, ConversationMessage, Portfolio, AdviceLog

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_chats = (await db.execute(select(func.count(ConversationMessage.id)))).scalar() or 0
    total_portfolios = (await db.execute(select(func.count(Portfolio.id)))).scalar() or 0
    total_advice = (await db.execute(select(func.count(AdviceLog.id)))).scalar() or 0

    # Activity by action type
    action_counts = await db.execute(
        select(ActivityLog.action, func.count(ActivityLog.id))
        .group_by(ActivityLog.action)
        .order_by(desc(func.count(ActivityLog.id)))
        .limit(20)
    )
    action_breakdown = {row[0]: row[1] for row in action_counts}

    return {
        "total_users": total_users,
        "total_chats": total_chats,
        "total_portfolios": total_portfolios,
        "total_advice_logs": total_advice,
        "action_breakdown": action_breakdown,
    }
