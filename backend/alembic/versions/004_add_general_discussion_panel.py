"""Add General Discussion panel

Revision ID: 004
Revises: 003
Create Date: 2026-06-05 00:00:00.000000

"""

import json
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PANEL_ID = "66666666-6666-6666-6666-666666666666"


def upgrade() -> None:
    from app.panels.seed_data import SYSTEM_PANELS

    panel = next(p for p in SYSTEM_PANELS if p["id"] == PANEL_ID)
    now = datetime.now(timezone.utc).isoformat()

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
    op.execute(
        sa.text("DELETE FROM panels WHERE id = CAST(:id AS uuid)").bindparams(id=PANEL_ID)
    )
