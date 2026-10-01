"""replace driver with tracker

Retire the Driver concept (username/password) in favour of a Tracker whose
pet-name ``id`` is the secret Traccar uniqueId / QR credential and whose
``nickname`` is the public label shown in GTFS-RT feeds.

This is a clean wipe: existing driver / driver_rule rows are dropped, not
migrated.

Revision ID: d7e8f9a0b1c2
Revises: f9af1255b125
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: str | Sequence[str] | None = "f9af1255b125"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clean wipe of the old Driver concept.
    op.drop_index("ix_driver_rule_driver_id", table_name="driver_rule")
    op.drop_table("driver_rule")
    op.drop_index(op.f("ix_driver_username"), table_name="driver")
    op.drop_table("driver")

    op.create_table(
        "tracker",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column(
            "nickname", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tracker_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tracker_id",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            sa.ForeignKey("tracker.id"),
            nullable=False,
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
    op.create_index("ix_tracker_rule_tracker_id", "tracker_rule", ["tracker_id"])


def downgrade() -> None:
    # Recreate the old (empty) Driver tables; data is not restored.
    op.drop_index("ix_tracker_rule_tracker_id", table_name="tracker_rule")
    op.drop_table("tracker_rule")
    op.drop_table("tracker")

    op.create_table(
        "driver",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_driver_username"), "driver", ["username"], unique=True)
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
