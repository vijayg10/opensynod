"""Org-level endpoints: session search, team members, invitations."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import AuditEvent, Session, TeamMembership, User
from app.db.session import get_db

router = APIRouter(prefix="/org", tags=["org"])


# ─────────────────────────────────────────────
# Session Search
# ─────────────────────────────────────────────


class SessionSummary(BaseModel):
    id: str
    topic: str
    outcome_type: str
    status: str
    phase: str | None
    panel_id: str | None
    cost_actual: float
    started_at: Any
    concluded_at: Any
    created_at: Any

    model_config = {"from_attributes": True}


@router.get("/sessions", response_model=list[SessionSummary])
async def search_sessions(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    panel_id: str | None = Query(default=None),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SessionSummary]:
    """Full-text session search with filters."""
    query = select(Session)

    if q:
        query = query.where(Session.topic.ilike(f"%{q}%"))
    if status_filter:
        query = query.where(Session.status == status_filter)
    if panel_id:
        query = query.where(Session.panel_id == panel_id)
    if from_date:
        query = query.where(Session.created_at >= from_date)
    if to_date:
        query = query.where(Session.created_at <= to_date)

    query = query.order_by(Session.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return [SessionSummary.model_validate(s) for s in result.scalars().all()]


# ─────────────────────────────────────────────
# Team Members
# ─────────────────────────────────────────────


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    display_name: str
    avatar_url: str | None
    role: str
    joined_at: Any

    model_config = {"from_attributes": True}


@router.get("/members", response_model=list[MemberResponse])
async def list_members(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MemberResponse]:
    """List all team members in the org."""
    result = await db.execute(
        select(TeamMembership, User)
        .join(User, TeamMembership.user_id == User.id)
        .order_by(TeamMembership.joined_at)
    )
    members = []
    for membership, user in result.all():
        members.append(
            MemberResponse(
                id=membership.id,
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                role=membership.role,
                joined_at=membership.joined_at,
            )
        )
    return members


class InviteRequest(BaseModel):
    email: str = Field(..., min_length=1)
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


@router.post("/members/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Invite a user to the org by email. Creates a placeholder user if not found."""
    result = await db.execute(select(User).where(User.email == body.email))
    invited_user = result.scalar_one_or_none()

    if not invited_user:
        # Create placeholder user; they'll set a password on first login
        invited_user = User(
            id=str(uuid.uuid4()),
            email=body.email,
            hashed_password="",
            display_name=body.email.split("@")[0],
            is_active=False,
        )
        db.add(invited_user)
        await db.flush()

    # Check if already a member (use a simple query)
    existing_result = await db.execute(
        select(TeamMembership).where(TeamMembership.user_id == invited_user.id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a team member")

    membership = TeamMembership(
        id=str(uuid.uuid4()),
        team_id=str(uuid.uuid4()),  # placeholder team_id for single-org mode
        user_id=invited_user.id,
        role=body.role,
    )
    db.add(membership)

    audit = AuditEvent(
        id=str(uuid.uuid4()),
        actor_id=current_user.id,
        actor_type="human",
        event_type="member_invited",
        payload_json={"email": body.email, "role": body.role},
    )
    db.add(audit)
    await db.commit()

    return {"user_id": invited_user.id, "email": body.email, "role": body.role}


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|member|viewer)$")


@router.patch("/members/{member_id}/role")
async def update_member_role(
    member_id: str,
    body: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Change a team member's role."""
    result = await db.execute(select(TeamMembership).where(TeamMembership.id == member_id))
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    old_role = membership.role
    membership.role = body.role

    audit = AuditEvent(
        id=str(uuid.uuid4()),
        actor_id=current_user.id,
        actor_type="human",
        event_type="member_role_updated",
        payload_json={"member_id": member_id, "old_role": old_role, "new_role": body.role},
    )
    db.add(audit)
    await db.commit()

    return {"member_id": member_id, "role": body.role}
