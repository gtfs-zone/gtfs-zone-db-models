"""add_driver_rule_table

Revision ID: 77c39735aa6a
Revises: f2a3b4c5d6e7
Create Date: 2026-04-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "77c39735aa6a"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "driver_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "driver_id", sa.Integer(), sa.ForeignKey("driver.id"), nullable=False
        ),
        sa.Column("trip_id", sa.String(256), nullable=False),
        sa.Column("monday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tuesday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("wednesday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("thursday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("friday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("saturday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sunday", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
    )
    op.create_index("ix_driver_rule_driver_id", "driver_rule", ["driver_id"])


def downgrade() -> None:
    op.drop_index("ix_driver_rule_driver_id", table_name="driver_rule")
    op.drop_table("driver_rule")
