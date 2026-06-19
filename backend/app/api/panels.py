"""Panel API endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Panel, User
from app.db.session import get_db
from app.panels.registry import PanelRegistry
from app.panels.schemas import PanelResponse, PanelSchema

router = APIRouter(prefix="/panels", tags=["panels"])


@router.get("", response_model=list[PanelResponse])
async def list_panels(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PanelResponse]:
    """List all available panels (system + org-custom)."""
    panels = await PanelRegistry.get_all(db)
    return [PanelResponse(**p.model_dump()) for p in panels]


@router.get("/{panel_id}", response_model=PanelResponse)
async def get_panel(
    panel_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PanelResponse:
    """Get a specific panel definition with all seat configurations."""
    panel = await PanelRegistry.get_by_id(db, panel_id)
    if not panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panel not found")
    return PanelResponse(**panel.model_dump())


class CreatePanelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    use_cases: list[str] = Field(default_factory=list)
    seats: list[dict[str, Any]] = Field(..., min_length=2)
    moderator_config: dict[str, Any] = Field(default_factory=dict)
    discussion_rules: dict[str, Any] = Field(default_factory=dict)


@router.post("", response_model=PanelResponse, status_code=status.HTTP_201_CREATED)
async def create_panel(
    body: CreatePanelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PanelResponse:
    """Create an org-custom panel. Validates model diversity before saving."""
    try:
        from app.panels.schemas import ModeratorConfig, PanelDiscussionRules, SeatConfig
        import uuid

        panel_id = str(uuid.uuid4())
        seats = [SeatConfig.model_validate(s) for s in body.seats]
        schema = PanelSchema(
            id=panel_id,
            name=body.name,
            description=body.description,
            use_cases=body.use_cases,
            seats=seats,
            moderator_config=ModeratorConfig.model_validate(body.moderator_config or {}),
            discussion_rules=PanelDiscussionRules.model_validate(body.discussion_rules or {}),
            is_system=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    db_panel = Panel(
        id=schema.id,
        name=schema.name,
        description=schema.description,
        use_cases=schema.use_cases,
        seats_json=[s.model_dump() for s in schema.seats],
        moderator_config_json=schema.moderator_config.model_dump(),
        discussion_rules_json=schema.discussion_rules.model_dump(),
        is_system=False,
        created_by=current_user.id,
    )
    db.add(db_panel)
    await db.commit()
    await db.refresh(db_panel)

    return PanelResponse(**schema.model_dump())


class UpdatePanelRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    use_cases: list[str] | None = None
    seats: list[dict[str, Any]] | None = None
    moderator_config: dict[str, Any] | None = None
    discussion_rules: dict[str, Any] | None = None


@router.patch("/{panel_id}", response_model=PanelResponse)
async def update_panel(
    panel_id: str,
    body: UpdatePanelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PanelResponse:
    """Update an org-custom panel. System panels cannot be updated."""
    from sqlalchemy import select as sa_select

    result = await db.execute(sa_select(Panel).where(Panel.id == panel_id))
    db_panel = result.scalar_one_or_none()
    if not db_panel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panel not found")
    if db_panel.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System panels cannot be modified")

    from app.panels.schemas import ModeratorConfig, PanelDiscussionRules, SeatConfig

    if body.name is not None:
        db_panel.name = body.name
    if body.description is not None:
        db_panel.description = body.description
    if body.use_cases is not None:
        db_panel.use_cases = body.use_cases
    if body.seats is not None:
        seats = [SeatConfig.model_validate(s) for s in body.seats]
        db_panel.seats_json = [s.model_dump() for s in seats]
    if body.moderator_config is not None:
        db_panel.moderator_config_json = ModeratorConfig.model_validate(body.moderator_config).model_dump()
    if body.discussion_rules is not None:
        db_panel.discussion_rules_json = PanelDiscussionRules.model_validate(body.discussion_rules).model_dump()

    await db.commit()
    await db.refresh(db_panel)

    from app.panels.registry import PanelRegistry
    refreshed = await PanelRegistry.get_by_id(db, panel_id)
    return PanelResponse(**refreshed.model_dump())
