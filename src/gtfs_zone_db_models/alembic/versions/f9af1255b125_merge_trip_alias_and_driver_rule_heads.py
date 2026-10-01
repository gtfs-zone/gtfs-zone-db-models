"""merge trip alias and driver rule heads

Revision ID: f9af1255b125
Revises: 457fca1b3d51, 77c39735aa6a
Create Date: 2026-05-03 17:25:38.278552

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f9af1255b125"
down_revision: str | Sequence[str] | None = ("457fca1b3d51", "77c39735aa6a")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
