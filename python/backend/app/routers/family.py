"""
Family router — family linking and household wealth view.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import FamilyLink, UserProfile, User

router = APIRouter(tags=["family"])


class LinkRequest(BaseModel):
    member_email: str
    relationship: str = "spouse"  # spouse | parent | child | sibling


class LinkResponse(BaseModel):
    id: str
    member_id: str
    relationship: str
    status: str


@router.post("/link", response_model=LinkResponse)
async def link_family_member(
    body: LinkRequest,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Send a family link request to another CREDA user."""
    result = await db.execute(
        select(User).where(User.email == body.member_email)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "User not found. They must have a CREDA account.")
    if member.id == auth.user_id:
        raise HTTPException(400, "Cannot link to yourself.")

    existing = await db.execute(
        select(FamilyLink).where(
            FamilyLink.owner_id == auth.user_id,
            FamilyLink.member_id == member.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Link already exists.")

    link = FamilyLink(
        owner_id=auth.user_id,
        member_id=member.id,
        relationship_type=body.relationship,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return LinkResponse(
        id=link.id,
        member_id=link.member_id,
        relationship=link.relationship_type,
        status="pending",
    )


@router.post("/accept/{link_id}")
async def accept_link(
    link_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pending family link request."""
    result = await db.execute(
        select(FamilyLink).where(
            FamilyLink.id == link_id,
            FamilyLink.member_id == auth.user_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Link request not found.")

    link.is_accepted = True
    await db.commit()
    return {"status": "accepted", "relationship": link.relationship_type}


@router.get("/members")
async def get_family_members(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get all linked family members with basic profile info."""
    result = await db.execute(
        select(FamilyLink).where(
            or_(FamilyLink.owner_id == auth.user_id, FamilyLink.member_id == auth.user_id),
            FamilyLink.is_accepted == True,
        )
    )
    links = result.scalars().all()

    members = []
    for link in links:
        member_id = link.member_id if link.owner_id == auth.user_id else link.owner_id
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == member_id)
        )
        profile = profile_result.scalar_one_or_none()

        members.append({
            "link_id": link.id,
            "member_id": member_id,
            "relationship": link.relationship_type,
            "name": profile.full_name if profile else "Unknown",
            "age": profile.age if profile else None,
        })

    return {"members": members, "total": len(members)}


@router.delete("/unlink/{link_id}")
async def unlink_member(
    link_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a family link."""
    result = await db.execute(
        select(FamilyLink).where(
            FamilyLink.id == link_id,
            or_(FamilyLink.owner_id == auth.user_id, FamilyLink.member_id == auth.user_id),
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Link not found.")

    await db.delete(link)
    await db.commit()
    return {"status": "unlinked"}
