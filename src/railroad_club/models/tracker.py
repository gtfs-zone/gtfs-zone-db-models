from typing import TYPE_CHECKING

import petname
from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.feed import Feed
    from railroad_club.models.tracker_rule import TrackerRule


def generate_tracker_id() -> str:
    """Return a random pet-name id (e.g. ``gently-tender-oyster``).

    This id doubles as the Traccar ``uniqueId`` / QR provisioning credential, so
    it is a secret and must never be exposed in a public GTFS-RT feed.
    """
    return petname.Generate(3, "-")


class Tracker(SQLModel, table=True):
    # ``id`` is the secret device credential (Traccar uniqueId / QR / Redis key).
    id: str = Field(
        default_factory=generate_tracker_id, primary_key=True, max_length=64
    )
    # ``nickname`` is the public label shown in GTFS-RT feeds.
    nickname: str = Field(max_length=64)
    feed_id: int = Field(foreign_key="feed.id")

    feed: "Feed" = Relationship(back_populates="trackers")
    rules: list["TrackerRule"] = Relationship(back_populates="tracker")

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("nickname must not be empty")
        return v

    def __str__(self) -> str:
        return self.nickname

    def __repr__(self) -> str:
        return f"Tracker(id={self.id!r}, nickname={self.nickname!r})"
