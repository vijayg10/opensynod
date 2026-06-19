"""Panel Registry: loads panel definitions from DB and validates them."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Panel
from app.panels.schemas import (
    ModeratorConfig,
    PanelDiscussionRules,
    PanelResponse,
    PanelSchema,
    SeatConfig,
)


def _detect_provider(model: str) -> str:
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith(("gpt-", "o3", "o1")):
        return "openai"
    if m.startswith("gemini"):
        return "google"
    return "ollama"


class PanelRegistry:
    """Loads and validates panel definitions from the database."""

    @staticmethod
    def db_to_schema(db_panel: Panel) -> PanelSchema:
        """Convert a DB Panel row to a validated PanelSchema."""
        seats_raw: list[Any] = db_panel.seats_json if isinstance(db_panel.seats_json, list) else []
        seats = [SeatConfig.model_validate(s) for s in seats_raw]

        moderator_config = ModeratorConfig.model_validate(
            db_panel.moderator_config_json or {}
        )
        discussion_rules = PanelDiscussionRules.model_validate(
            db_panel.discussion_rules_json or {}
        )

        return PanelSchema(
            id=db_panel.id,
            name=db_panel.name,
            description=db_panel.description,
            use_cases=db_panel.use_cases if isinstance(db_panel.use_cases, list) else [],
            seats=seats,
            moderator_config=moderator_config,
            discussion_rules=discussion_rules,
            is_system=db_panel.is_system,
        )

    @staticmethod
    def to_response(db_panel: Panel) -> PanelResponse:
        schema = PanelRegistry.db_to_schema(db_panel)
        return PanelResponse(**schema.model_dump())

    @staticmethod
    async def get_all(db: AsyncSession) -> list[PanelSchema]:
        result = await db.execute(select(Panel).order_by(Panel.name))
        panels = result.scalars().all()
        return [PanelRegistry.db_to_schema(p) for p in panels]

    @staticmethod
    async def get_by_id(db: AsyncSession, panel_id: str) -> PanelSchema | None:
        result = await db.execute(select(Panel).where(Panel.id == panel_id))
        db_panel = result.scalar_one_or_none()
        if db_panel is None:
            return None
        return PanelRegistry.db_to_schema(db_panel)

    @staticmethod
    def build_snapshot(panel: PanelSchema) -> dict[str, Any]:
        """Snapshot a panel for immutable storage in sessions.panel_snapshot_json."""
        return panel.model_dump()
