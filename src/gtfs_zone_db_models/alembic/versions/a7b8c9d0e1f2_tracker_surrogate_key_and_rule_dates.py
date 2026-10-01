"""tracker surrogate key, rule dates, and rule exceptions

Three changes that have to land together because they share a table.

1. ``Tracker.id`` stops being the Traccar credential. It becomes a uuid4-hex
   surrogate, safe to log and to put in a URL, and the credential moves to
   ``device_key`` (unique, indexed), which keeps the pet-name format. Existing
   ids are copied across, so every provisioned device keeps working.
2. ``TrackerRule`` gains ``start_date``/``end_date`` and its ``start_time`` /
   ``end_time`` become seconds since service midnight, GTFS-shaped, so a
   window that crosses midnight is expressible at all.
3. ``tracker_rule_exception`` adds per-date overrides.

Existing rules are backfilled with a start of today and an open-ended end, so
nothing silently stops running. Times convert as ``h*3600 + m*60 + s``: a rule
that already had ``start_time > end_time`` was inexpressible and matched on no
day, and it stays dead rather than being resurrected on a guess.

``(feed_id, nickname)`` becomes unique. Nickname is no longer an identity key,
but it is still the public GTFS-RT vehicle label.

Revision ID: a7b8c9d0e1f2
Revises: d07e8cb15a7a
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "d07e8cb15a7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- tracker: split identity from credential ---------------------------
    op.add_column("tracker", sa.Column("device_key", sa.String(64), nullable=True))
    op.add_column("tracker", sa.Column("new_id", sa.String(32), nullable=True))
    # The old id *is* the credential; md5 over it plus a clock reading gives a
    # 32-hex surrogate that is unique because the old id already was.
    op.execute(
        "UPDATE tracker SET device_key = id, "
        "new_id = md5(id || clock_timestamp()::text)"
    )
    op.alter_column("tracker", "device_key", nullable=False)
    op.alter_column("tracker", "new_id", nullable=False)

    # --- tracker_rule: repoint the FK at the surrogate ---------------------
    op.add_column("tracker_rule", sa.Column("new_tracker_id", sa.String(32)))
    op.execute(
        "UPDATE tracker_rule SET new_tracker_id = tracker.new_id "
        "FROM tracker WHERE tracker_rule.tracker_id = tracker.id"
    )
    op.drop_constraint("tracker_rule_tracker_id_fkey", "tracker_rule")
    op.drop_index("ix_tracker_rule_tracker_id", table_name="tracker_rule")
    op.drop_column("tracker_rule", "tracker_id")
    op.alter_column("tracker_rule", "new_tracker_id", new_column_name="tracker_id")
    op.alter_column("tracker_rule", "tracker_id", nullable=False)

    op.drop_constraint("tracker_pkey", "tracker")
    op.drop_column("tracker", "id")
    op.alter_column("tracker", "new_id", new_column_name="id")
    op.create_primary_key("tracker_pkey", "tracker", ["id"])
    op.create_index("ix_tracker_device_key", "tracker", ["device_key"], unique=True)
    op.create_unique_constraint(
        "uq_tracker_feed_id_nickname", "tracker", ["feed_id", "nickname"]
    )

    op.create_foreign_key(
        "tracker_rule_tracker_id_fkey",
        "tracker_rule",
        "tracker",
        ["tracker_id"],
        ["id"],
    )
    op.create_index("ix_tracker_rule_tracker_id", "tracker_rule", ["tracker_id"])

    # --- tracker_rule: dates and service-midnight seconds ------------------
    op.add_column(
        "tracker_rule",
        sa.Column(
            "start_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
    )
    op.add_column("tracker_rule", sa.Column("end_date", sa.Date(), nullable=True))
    op.alter_column("tracker_rule", "start_date", server_default=None)

    op.add_column("tracker_rule", sa.Column("start_seconds", sa.Integer()))
    op.add_column("tracker_rule", sa.Column("end_seconds", sa.Integer()))
    op.execute(
        "UPDATE tracker_rule SET "
        "start_seconds = EXTRACT(EPOCH FROM start_time)::int, "
        "end_seconds = EXTRACT(EPOCH FROM end_time)::int"
    )
    op.drop_column("tracker_rule", "start_time")
    op.drop_column("tracker_rule", "end_time")
    op.alter_column("tracker_rule", "start_seconds", new_column_name="start_time")
    op.alter_column("tracker_rule", "end_seconds", new_column_name="end_time")
    op.alter_column("tracker_rule", "start_time", nullable=False)
    op.alter_column("tracker_rule", "end_time", nullable=False)

    # --- per-date overrides ------------------------------------------------
    op.create_table(
        "tracker_rule_exception",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("exception_type", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["tracker_rule.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("rule_id", "date", name="uq_tracker_rule_exception_date"),
    )
    op.create_index(
        "ix_tracker_rule_exception_rule_id", "tracker_rule_exception", ["rule_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tracker_rule_exception_rule_id", table_name="tracker_rule_exception"
    )
    op.drop_table("tracker_rule_exception")

    op.add_column("tracker_rule", sa.Column("start_clock", sa.Time()))
    op.add_column("tracker_rule", sa.Column("end_clock", sa.Time()))
    # Seconds past 24h have no `time` to go back to; they wrap.
    op.execute(
        "UPDATE tracker_rule SET "
        "start_clock = (TIME '00:00' + (start_time % 86400) * INTERVAL '1 second'), "
        "end_clock = (TIME '00:00' + (end_time % 86400) * INTERVAL '1 second')"
    )
    op.drop_column("tracker_rule", "start_time")
    op.drop_column("tracker_rule", "end_time")
    op.alter_column("tracker_rule", "start_clock", new_column_name="start_time")
    op.alter_column("tracker_rule", "end_clock", new_column_name="end_time")
    op.alter_column("tracker_rule", "start_time", nullable=False)
    op.alter_column("tracker_rule", "end_time", nullable=False)
    op.drop_column("tracker_rule", "end_date")
    op.drop_column("tracker_rule", "start_date")

    # Put the credential back in the primary key.
    op.drop_index("ix_tracker_rule_tracker_id", table_name="tracker_rule")
    op.drop_constraint("tracker_rule_tracker_id_fkey", "tracker_rule")
    # Widen before writing: device_key is up to 64 chars, the column is 32.
    op.alter_column("tracker_rule", "tracker_id", type_=sa.String(64))
    op.execute(
        "UPDATE tracker_rule SET tracker_id = tracker.device_key "
        "FROM tracker WHERE tracker_rule.tracker_id = tracker.id"
    )

    op.drop_constraint("uq_tracker_feed_id_nickname", "tracker")
    op.drop_index("ix_tracker_device_key", table_name="tracker")
    op.drop_constraint("tracker_pkey", "tracker")
    op.alter_column("tracker", "id", type_=sa.String(64))
    op.execute("UPDATE tracker SET id = device_key")
    op.create_primary_key("tracker_pkey", "tracker", ["id"])
    op.drop_column("tracker", "device_key")

    op.create_foreign_key(
        "tracker_rule_tracker_id_fkey",
        "tracker_rule",
        "tracker",
        ["tracker_id"],
        ["id"],
    )
    op.create_index("ix_tracker_rule_tracker_id", "tracker_rule", ["tracker_id"])
