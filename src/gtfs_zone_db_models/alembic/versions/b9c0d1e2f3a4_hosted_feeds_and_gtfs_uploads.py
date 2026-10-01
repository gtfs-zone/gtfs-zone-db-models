"""hosted feeds and the gtfs_upload history

A feed's schedule can be *uploaded* rather than *linked*. ``Feed.source_kind``
says which; every existing row is ``'url'``, which is exactly what it is, so
the backfill is unconditional and nothing changes behaviour.

``gtfs_upload`` is the history: one row per zip, kept, so a bad upload rolls
back to the one before it. ``Feed.current_upload_id`` points at whichever is
being served. The two tables reference each other, so that foreign key is
created with ``use_alter``: it is an ``ALTER TABLE`` after both exist rather
than part of either ``CREATE TABLE``, which have no valid order otherwise.

``static_feed_url`` becomes nullable, since a hosted feed does not have one.
Every reader had assumed a value was there.

Revision ID: b9c0d1e2f3a4
Revises: a7b8c9d0e1f2
Create Date: 2026-08-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gtfs_upload",
        sa.Column("id", sa.String(32), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feed.id"]),
        # The uploader can be deleted; the record of the upload cannot.
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_gtfs_upload_feed_id", "gtfs_upload", ["feed_id"])

    # Nullable, backfilled, then made NOT NULL: a server_default would stay on
    # the column and quietly answer for a future insert that forgot to say.
    op.add_column("feed", sa.Column("source_kind", sa.String(16), nullable=True))
    op.execute("UPDATE feed SET source_kind = 'url'")
    op.alter_column("feed", "source_kind", nullable=False)

    op.add_column("feed", sa.Column("current_upload_id", sa.String(32), nullable=True))
    op.create_foreign_key(
        "fk_feed_current_upload_id",
        "feed",
        "gtfs_upload",
        ["current_upload_id"],
        ["id"],
        use_alter=True,
    )

    op.alter_column(
        "feed", "static_feed_url", existing_type=sa.VARCHAR(), nullable=True
    )


def downgrade() -> None:
    # A hosted feed has no URL to put back, so it would violate the NOT NULL.
    # Refusing is better than inventing one or dropping the feed.
    hosted = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM feed WHERE source_kind = 'hosted'"))
        .scalar_one()
    )
    if hosted:
        raise RuntimeError(
            f"{hosted} feed(s) are hosted and have no static_feed_url; "
            "repoint them at a URL before downgrading"
        )

    op.alter_column(
        "feed", "static_feed_url", existing_type=sa.VARCHAR(), nullable=False
    )
    op.drop_constraint("fk_feed_current_upload_id", "feed", type_="foreignkey")
    op.drop_column("feed", "current_upload_id")
    op.drop_column("feed", "source_kind")
    op.drop_index("ix_gtfs_upload_feed_id", table_name="gtfs_upload")
    op.drop_table("gtfs_upload")
