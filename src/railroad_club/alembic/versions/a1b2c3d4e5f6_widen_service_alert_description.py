"""widen service_alert.description_text to unbounded text

Amtrak's alerts-page scrape (hell-gate-bridge) includes the full detail-page
body in the description, which routinely exceeds the 2048-char varchar cap
and 500s the whole /ingest/alerts batch (all-or-nothing insert). Nothing else
depends on the description having a bounded length, so drop the cap instead
of picking a new arbitrary one.

Revision ID: a1b2c3d4e5f6
Revises: e8f9a0b1c2d3
Create Date: 2026-08-03 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "e8f9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "service_alert",
        "description_text",
        existing_type=sa.String(length=2048),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "service_alert",
        "description_text",
        existing_type=sa.Text(),
        type_=sa.String(length=2048),
        existing_nullable=False,
    )
