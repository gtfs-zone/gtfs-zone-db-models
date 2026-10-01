"""drop trip alias table

Revision ID: f3a4b5c6d7e8
Revises: d7e8f9a0b1c2
Create Date: 2026-07-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: str | Sequence[str] | None = "d7e8f9a0b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("tripalias")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "tripalias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=64), nullable=False),
        sa.Column("trip_id", sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(
            ["feed_id"],
            ["feed.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", "alias"),
    )
