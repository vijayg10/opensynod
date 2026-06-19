"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # teams
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_teams_slug", "teams", ["slug"])

    # team_memberships
    op.create_table(
        "team_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("admin", "member", "viewer", name="membership_role", create_type=False),
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_team_memberships_team_id", "team_memberships", ["team_id"])
    op.create_index("ix_team_memberships_user_id", "team_memberships", ["user_id"])

    # panels
    op.create_table(
        "panels",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("use_cases", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("seats_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("moderator_config_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("discussion_rules_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column(
            "outcome_type",
            sa.Enum(
                "recommendation",
                "exploration",
                "risk_assessment",
                name="outcome_type",
                create_type=False,
            ),
            nullable=False,
            server_default="recommendation",
        ),
        sa.Column("success_criteria", sa.Text(), nullable=True),
        sa.Column("context_documents_json", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("panel_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("panels.id"), nullable=True),
        sa.Column("panel_snapshot_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("discussion_rules_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        sa.Column("cost_actual", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost_limit", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "queued", "running", "paused", "voting", "concluded", "failed",
                name="session_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "phase",
            sa.Enum(
                "opening", "exploration", "debate", "convergence", "vote",
                name="discussion_phase",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_sessions_org_id", "sessions", ["org_id"])
    op.create_index("ix_sessions_created_by", "sessions", ["created_by"])
    op.create_index("ix_sessions_status", "sessions", ["status"])

    # session_participants
    op.create_table(
        "session_participants",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "participant_type",
            sa.Enum("agent", "human", name="participant_type", create_type=False),
            nullable=False,
        ),
        sa.Column("seat_id", sa.String(255), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_session_participants_session_id", "session_participants", ["session_id"])

    # messages (append-only enforced by trigger)
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seat_id", sa.String(255), nullable=True),
        sa.Column(
            "author_type",
            sa.Enum("agent", "human", "moderator", "system", name="author_type", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("reasoning_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("sources_cited_json", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phase_at_creation", sa.String(50), nullable=True),
        sa.Column("content_search", postgresql.TSVECTOR(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_index("ix_messages_seat_id", "messages", ["seat_id"])
    op.create_index(
        "ix_messages_content_search", "messages", ["content_search"], postgresql_using="gin"
    )

    # Trigger: keep content_search in sync with content
    op.execute("""
        CREATE OR REPLACE FUNCTION messages_content_search_update() RETURNS trigger AS $$
        BEGIN
            NEW.content_search := to_tsvector('english', NEW.content);
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER messages_content_search_trigger
        BEFORE INSERT OR UPDATE ON messages
        FOR EACH ROW EXECUTE FUNCTION messages_content_search_update();
    """)

    # Append-only trigger for messages
    op.execute("""
        CREATE OR REPLACE FUNCTION deny_messages_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'messages table is append-only: UPDATE and DELETE are not permitted';
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER messages_append_only
        BEFORE UPDATE OR DELETE ON messages
        FOR EACH ROW EXECUTE FUNCTION deny_messages_mutation();
    """)

    # sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False, server_default=""),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("retrieval_seat_id", sa.String(255), nullable=True),
        sa.Column("quality_signals_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("flagged_by_json", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("flag_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_sources_session_id", "sources", ["session_id"])

    # votes
    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voter_id", sa.String(255), nullable=False),
        sa.Column(
            "voter_type",
            sa.Enum("agent", "human", name="voter_type", create_type=False),
            nullable=False,
        ),
        sa.Column("recommendation_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "vote",
            sa.Enum("yes", "no", "abstain", name="vote_choice", create_type=False),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_votes_session_id", "votes", ["session_id"])

    # outcomes
    op.create_table(
        "outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum("recommendation", "no_consensus", name="outcome_result_type", create_type=False),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False, server_default=""),
        sa.Column("supporting_arguments_json", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("substantive_dissents_json", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("agent_vote_summary_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("human_vote_summary_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("divergence_noted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("source_density_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outcomes_session_id", "outcomes", ["session_id"])

    # decision_outcomes
    op.create_table(
        "decision_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("marked_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "marked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.Enum(
                "adopted_success",
                "adopted_failure",
                "chose_differently",
                name="decision_result",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_decision_outcomes_session_id", "decision_outcomes", ["session_id"])

    # audit_events (append-only enforced by trigger)
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_events_session_id", "audit_events", ["session_id"])
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # Append-only trigger for audit_events
    op.execute("""
        CREATE OR REPLACE FUNCTION deny_audit_events_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events table is append-only: UPDATE and DELETE are not permitted';
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION deny_audit_events_mutation();
    """)


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("decision_outcomes")
    op.drop_table("outcomes")
    op.drop_table("votes")
    op.drop_table("sources")
    op.drop_table("messages")
    op.drop_table("session_participants")
    op.drop_table("sessions")
    op.drop_table("panels")
    op.drop_table("team_memberships")
    op.drop_table("teams")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    for enum_name in [
        "membership_role", "outcome_type", "session_status", "discussion_phase",
        "participant_type", "author_type", "voter_type", "vote_choice",
        "outcome_result_type", "decision_result",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
