"""Seed 5 system panels

Revision ID: 002
Revises: 001
Create Date: 2026-05-16 00:01:00.000000

"""

import json
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.panels.seed_data import SYSTEM_PANELS

    now = datetime.now(timezone.utc).isoformat()

    for panel in SYSTEM_PANELS:
        op.execute(
            sa.text(
                """
                INSERT INTO panels
                    (id, name, description, use_cases, seats_json,
                     moderator_config_json, discussion_rules_json,
                     is_system, created_by, created_at, updated_at)
                VALUES
                    (CAST(:id AS uuid), :name, :description,
                     CAST(:use_cases AS json), CAST(:seats_json AS json),
                     CAST(:moderator_config_json AS json), CAST(:discussion_rules_json AS json),
                     :is_system, CAST(:created_by AS uuid),
                     CAST(:created_at AS timestamptz), CAST(:updated_at AS timestamptz))
                ON CONFLICT (id) DO NOTHING
                """
            ).bindparams(
                id=panel["id"],
                name=panel["name"],
                description=panel["description"],
                use_cases=json.dumps(panel["use_cases"]),
                seats_json=json.dumps(panel["seats"]),
                moderator_config_json=json.dumps(panel["moderator_config"]),
                discussion_rules_json=json.dumps(panel["discussion_rules"]),
                is_system=True,
                created_by=None,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    from app.panels.seed_data import SYSTEM_PANELS

    for panel in SYSTEM_PANELS:
        op.execute(
            sa.text("DELETE FROM panels WHERE id = :id").bindparams(id=panel["id"])
        )
