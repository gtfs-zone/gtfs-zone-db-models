"""add feed_member

Lets a feed be worked on by people other than its owner. Members get the same
access to the feed's contents; ownership stays on ``feed.owner_id`` and is not
duplicated here, so "is owner" is never ambiguous.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-08-03 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: str | Sequence[str] | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feed_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("added_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        # One membership row per person per feed.
        sa.UniqueConstraint("feed_id", "user_id"),
    )
    op.create_index("ix_feed_member_feed_id", "feed_member", ["feed_id"])
    op.create_index("ix_feed_member_user_id", "feed_member", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_feed_member_user_id", table_name="feed_member")
    op.drop_index("ix_feed_member_feed_id", table_name="feed_member")
    op.drop_table("feed_member")
