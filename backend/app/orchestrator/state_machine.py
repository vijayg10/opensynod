"""Discussion state machine: validates transitions and writes audit events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent, Session

# Valid transitions: current_status -> allowed next statuses
_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["queued"],
    "queued": ["running", "failed"],
    "running": ["paused", "voting", "failed"],
    "paused": ["running", "failed"],
    "voting": ["concluded", "failed"],
    "concluded": [],
    "failed": ["queued"],
}

# Valid phase transitions (must be in order)
_PHASE_ORDER = ["opening", "exploration", "debate", "convergence", "vote"]


class InvalidTransitionError(Exception):
    pass


class StateMachine:
    """Handles session status and phase transitions with audit trail."""

    @staticmethod
    def can_transition_status(current: str, new: str) -> bool:
        return new in _STATUS_TRANSITIONS.get(current, [])

    @staticmethod
    def can_transition_phase(current: str | None, new: str) -> bool:
        if current is None:
            return new == "opening"
        try:
            curr_idx = _PHASE_ORDER.index(current)
            new_idx = _PHASE_ORDER.index(new)
            return new_idx == curr_idx + 1
        except ValueError:
            return False

    @staticmethod
    async def transition_status(
        db: AsyncSession,
        session: Session,
        new_status: str,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not StateMachine.can_transition_status(session.status, new_status):
            raise InvalidTransitionError(
                f"Cannot transition session from '{session.status}' to '{new_status}'"
            )

        old_status = session.status
        session.status = new_status

        if new_status == "running" and session.started_at is None:
            session.started_at = datetime.now(timezone.utc)
        if new_status == "concluded":
            session.concluded_at = datetime.now(timezone.utc)

        audit = AuditEvent(
            id=str(uuid.uuid4()),
            session_id=session.id,
            actor_id=actor_id,
            actor_type="system",
            event_type=f"session_status_{new_status}",
            payload_json={
                "from_status": old_status,
                "to_status": new_status,
                **(payload or {}),
            },
        )
        db.add(audit)
        await db.flush()

    @staticmethod
    async def transition_phase(
        db: AsyncSession,
        session: Session,
        new_phase: str,
        summary: str | None = None,
    ) -> None:
        old_phase = session.phase
        session.phase = new_phase

        audit = AuditEvent(
            id=str(uuid.uuid4()),
            session_id=session.id,
            actor_type="system",
            event_type="phase_transition",
            payload_json={
                "from_phase": old_phase,
                "to_phase": new_phase,
                "summary": summary,
            },
        )
        db.add(audit)
        await db.flush()
