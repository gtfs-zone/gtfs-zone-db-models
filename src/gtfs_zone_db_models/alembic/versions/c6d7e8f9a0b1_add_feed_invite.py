"""add feed_invite

Lets a feed be shared with someone who has never signed in. The row is claimed
on their first login, when a verified address matches.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-08-03 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: str | Sequence[str] | None = "b5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feed_invite",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["claimed_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feed_invite_feed_id", "feed_invite", ["feed_id"])
    op.create_index("ix_feed_invite_email", "feed_invite", ["email"])
    # At most one *outstanding* invite per address per feed. Claimed rows are
    # kept as history and are deliberately outside the constraint.
    op.create_index(
        "uq_feed_invite_open",
        "feed_invite",
        ["feed_id", "email"],
        unique=True,
        postgresql_where=sa.text("claimed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_feed_invite_open", table_name="feed_invite")
    op.drop_index("ix_feed_invite_email", table_name="feed_invite")
    op.drop_index("ix_feed_invite_feed_id", table_name="feed_invite")
    op.drop_table("feed_invite")
