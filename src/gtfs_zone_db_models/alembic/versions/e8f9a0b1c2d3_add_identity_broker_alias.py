"""add identity.broker_alias and identity.last_seen_at

``provider`` is the OIDC issuer and reads ``keycloak`` for every row, which
says nothing about how someone actually signed in. Keycloak knows: it sets an
``identity_provider`` session note on a brokered login, so record it and show
it, and record when the credential was last used. Both are display-only: the
account page is where a duplicate or dormant principal has to become obvious,
and neither column may be matched or authorised on.

Nullable, with no backfill. An existing row fills itself in the next time that
credential signs in, and a row that never signs in again is precisely the one
worth seeing as blank.

Revision ID: e8f9a0b1c2d3
Revises: c6d7e8f9a0b1
Create Date: 2026-08-03 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: str | Sequence[str] | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "identity",
        sa.Column("broker_alias", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "identity",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("identity", "last_seen_at")
    op.drop_column("identity", "broker_alias")
