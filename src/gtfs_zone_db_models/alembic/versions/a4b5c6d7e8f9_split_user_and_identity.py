"""split user and identity

Separates the person (``user``) from the credential (``identity``), so one
person can sign in through several providers (GitHub and Google, say) and
land on the same account. ``user.provider`` / ``user.provider_subject`` move
into ``identity``, one row per login method.

``user.id`` is deliberately preserved: ``feed.owner_id`` points at it, so the
backfill must not renumber anyone.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-08-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | Sequence[str] | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "provider_subject", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "email_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subject"),
    )
    op.create_index("ix_identity_user_id", "identity", ["user_id"])
    op.create_index("ix_identity_email", "identity", ["email"])

    # One identity per existing user, carrying its current provider pair.
    #
    # These subjects are whatever the old provider happened to emit and will
    # not match what a new IdP sends; a separate remap handles that at cutover.
    # The point of the backfill is to keep `user.id`, and therefore feed
    # ownership, intact.
    #
    # email_verified stays false: nothing recorded whether it ever was, and
    # guessing true here would hand account-linking a forged match to trust.
    op.execute(
        """
        INSERT INTO identity
            (user_id, provider, provider_subject, email, email_verified, linked_at)
        SELECT id, provider, provider_subject, email, false, now()
        FROM "user"
        """
    )

    op.add_column(
        "user",
        sa.Column("primary_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute('UPDATE "user" SET primary_email = email, created_at = now()')
    op.alter_column("user", "created_at", nullable=False)
    op.create_index("ix_user_primary_email", "user", ["primary_email"])

    op.drop_constraint("uq_user_provider_subject", "user", type_="unique")
    op.drop_column("user", "provider")
    op.drop_column("user", "provider_subject")
    op.drop_column("user", "email")


def downgrade() -> None:
    """Collapse each user's *earliest* identity back onto the user row.

    This is lossy on purpose and does not round-trip: a user who has genuinely
    linked two providers has only one provider pair to come back to, and the
    others are dropped. Downgrading past this point after anyone has linked an
    account means those users can only sign in through their first provider.
    """
    op.add_column(
        "user", sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column(
            "provider_subject", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.add_column(
        "user", sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )

    op.execute(
        """
        UPDATE "user" u
        SET provider = i.provider,
            provider_subject = i.provider_subject,
            email = COALESCE(i.email, u.primary_email)
        FROM (
            SELECT DISTINCT ON (user_id) user_id, provider, provider_subject, email
            FROM identity
            ORDER BY user_id, linked_at, id
        ) i
        WHERE i.user_id = u.id
        """
    )
    # Users created after the split have no identity only if something went
    # wrong, but NOT NULL would fail on them, so give them a placeholder that
    # cannot collide with a real subject.
    op.execute(
        """
        UPDATE "user"
        SET provider = 'unknown', provider_subject = 'orphaned-user-' || id
        WHERE provider IS NULL
        """
    )
    op.alter_column("user", "provider", nullable=False)
    op.alter_column("user", "provider_subject", nullable=False)
    op.create_unique_constraint(
        "uq_user_provider_subject", "user", ["provider", "provider_subject"]
    )

    op.drop_index("ix_user_primary_email", table_name="user")
    op.drop_column("user", "created_at")
    op.drop_column("user", "primary_email")

    op.drop_index("ix_identity_email", table_name="identity")
    op.drop_index("ix_identity_user_id", table_name="identity")
    op.drop_table("identity")
