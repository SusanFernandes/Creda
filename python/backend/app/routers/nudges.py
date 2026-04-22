"""
Nudges router — proactive financial notifications.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Nudge

router = APIRouter()


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
