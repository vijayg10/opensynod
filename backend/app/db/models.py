"""SQLAlchemy ORM models for AI Round Table Conference.

All tables use UUID primary keys. append-only enforcement for messages and
audit_events is implemented via Alembic migration triggers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")
    team_memberships: Mapped[list[TeamMembership]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memberships: Mapped[list[TeamMembership]] = relationship(back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    team_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        Enum("admin", "member", "viewer", name="membership_role", create_type=False), nullable=False, default="member"
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Team] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="team_memberships")


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------


class Panel(Base):
    __tablename__ = "panels"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    use_cases: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    seats_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    moderator_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    discussion_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_type: Mapped[str] = mapped_column(
        Enum("recommendation", "exploration", "risk_assessment", name="outcome_type", create_type=False),
        nullable=False,
        default="recommendation",
    )
    success_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_documents_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    panel_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("panels.id"), nullable=True
    )
    panel_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    discussion_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cost_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_actual: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("draft", "queued", "running", "paused", "voting", "concluded", "failed",
             name="session_status", create_type=False),
        nullable=False,
        default="draft",
        index=True,
    )
    phase: Mapped[str | None] = mapped_column(
        Enum("opening", "exploration", "debate", "convergence", "vote", name="discussion_phase", create_type=False),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    participants: Mapped[list[SessionParticipant]] = relationship(back_populates="session")
    messages: Mapped[list[Message]] = relationship(back_populates="session")
    sources: Mapped[list[Source]] = relationship(back_populates="session")
    votes: Mapped[list[Vote]] = relationship(back_populates="session")
    outcomes: Mapped[list[Outcome]] = relationship(back_populates="session")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="session")


class SessionParticipant(Base):
    __tablename__ = "session_participants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_type: Mapped[str] = mapped_column(
        Enum("agent", "human", name="participant_type", create_type=False), nullable=False
    )
    seat_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[Session] = relationship(back_populates="participants")


# ---------------------------------------------------------------------------
# Messages (append-only)
# ---------------------------------------------------------------------------


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seat_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    author_type: Mapped[str] = mapped_column(
        Enum("agent", "human", "moderator", "system", name="author_type", create_type=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sources_cited_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    phase_at_creation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_search: Mapped[Any] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_content_search", "content_search", postgresql_using="gin"),
    )


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retrieval_seat_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quality_signals_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    flagged_by_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    flag_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[Session] = relationship(back_populates="sources")


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    voter_id: Mapped[str] = mapped_column(String(255), nullable=False)
    voter_type: Mapped[str] = mapped_column(
        Enum("agent", "human", name="voter_type", create_type=False), nullable=False
    )
    recommendation_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    vote: Mapped[str] = mapped_column(
        Enum("yes", "no", "abstain", name="vote_choice", create_type=False), nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="votes")


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        Enum("recommendation", "no_consensus", name="outcome_result_type", create_type=False), nullable=False
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    supporting_arguments_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    substantive_dissents_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    agent_vote_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    human_vote_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    divergence_noted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_density_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[Session] = relationship(back_populates="outcomes")


class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marked_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    result: Mapped[str] = mapped_column(
        Enum(
            "adopted_success", "adopted_failure", "chose_differently",
            name="decision_result", create_type=False
        ),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Audit (append-only)
# ---------------------------------------------------------------------------


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    actor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    actor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    session: Mapped[Session | None] = relationship(back_populates="audit_events")
