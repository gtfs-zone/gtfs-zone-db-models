from typing import TYPE_CHECKING
from uuid import uuid4

import petname
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import validates
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.feed import Feed
    from railroad_club.models.tracker_rule import TrackerRule


def generate_device_key() -> str:
    """Return a random pet-name device key (e.g. ``gently-tender-oyster``).

    This is the Traccar ``uniqueId`` / QR provisioning credential, so it is a
    secret and must never be exposed in a public GTFS-RT feed. Pet-name shaped
    because someone types it into the Traccar client by hand when the QR flow
    fails.
    """
    return petname.Generate(3, "-")


def generate_tracker_id() -> str:
    """Return a random surrogate primary key. Not a secret.

    Colon-free, which ``validate_id`` below requires of every tracker id.
    """
    return uuid4().hex


class Tracker(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("feed_id", "nickname"),)

    # A surrogate key, safe to put in a URL, a log line or a Redis key. Never
    # contains a colon; see ``validate_id``.
    id: str = Field(
        default_factory=generate_tracker_id, primary_key=True, max_length=32
    )
    # The secret Traccar credential. Served only by the tracker detail and
    # provisioning routes.
    device_key: str = Field(
        default_factory=generate_device_key, unique=True, index=True, max_length=64
    )
    # ``nickname`` is the public label shown in GTFS-RT feeds.
    nickname: str = Field(max_length=64)
    feed_id: int = Field(foreign_key="feed.id")

    feed: "Feed" = Relationship(back_populates="trackers")
    rules: list["TrackerRule"] = Relationship(back_populates="tracker")

    # ``@validates``, not ``@field_validator``: a SQLModel ``table=True`` model
    # skips Pydantic validation on init, so a field validator here never runs.
    # The SQLAlchemy hook fires on attribute set, which includes ``__init__``.

    @validates("id")
    def validate_id(self, _key: str, value: str) -> str:
        """Reject a colon, which the Redis keyspace cannot encode.

        ``vehicle:{id}:{vehicle_id}`` is built and split on the first colon, so
        a colon in the id makes that encoding ambiguous: ``("a:b", "c")`` and
        ``("a", "b:c")`` collide on one key and two vehicles share a record.
        This is the only place the rule is enforced - ids are born here or not
        at all - so ``railroad_club.vehicle_keys`` may assume it.
        """
        if ":" in value:
            raise ValueError("tracker id must not contain ':'")
        return value

    @validates("nickname")
    def validate_nickname(self, _key: str, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("nickname must not be empty")
        return value

    def __str__(self) -> str:
        return self.nickname

    def __repr__(self) -> str:
        # No device_key: this lands in logs and tracebacks.
        return f"Tracker(id={self.id!r}, nickname={self.nickname!r})"
