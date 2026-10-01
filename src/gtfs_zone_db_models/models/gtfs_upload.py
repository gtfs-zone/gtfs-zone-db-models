from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from gtfs_zone_db_models.models.feed import Feed


class FeedSourceKind(StrEnum):
    """Where a feed's schedule zip comes from."""

    # Somebody else's URL, downloaded over HTTP on every refresh.
    url = "url"
    # A zip somebody uploaded, held in object storage and served back by us.
    hosted = "hosted"


def generate_upload_id() -> str:
    """A surrogate primary key, known before the row is inserted.

    The object key contains it, and the object is written before the row is
    committed, so it cannot be a sequence the database hands back afterwards.
    Not a secret, but not guessable either, which matters because the key is
    the only thing between the store and a stranger.
    """
    return uuid4().hex


class GtfsUpload(SQLModel, table=True):
    """One uploaded GTFS zip. Every upload is kept, so a bad one rolls back."""

    __tablename__ = "gtfs_upload"

    id: str = Field(default_factory=generate_upload_id, primary_key=True, max_length=32)
    feed_id: int = Field(foreign_key="feed.id", index=True)
    # Where the bytes are in the bucket. Built by ``object_key_for``, which is
    # the only place the layout is written down.
    object_key: str = Field(unique=True, max_length=255)
    # Hex digest of the bytes as stored. Serves as the public route's ETag.
    sha256: str = Field(max_length=64)
    size_bytes: int
    # What the uploader called it. Shown in the history and nowhere else: it is
    # a person's filename and never touches the object key.
    original_filename: str = Field(max_length=255)
    # Nullable so deleting an account does not delete the feed's history. The
    # row says an upload happened even once nobody is left to attribute it to.
    uploaded_by_user_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
        ),
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    feed: "Feed" = Relationship(
        back_populates="uploads",
        sa_relationship_kwargs={"foreign_keys": "[GtfsUpload.feed_id]"},
    )

    def __repr__(self) -> str:
        return (
            f"GtfsUpload(id={self.id!r}, feed_id={self.feed_id}, "
            f"size={self.size_bytes})"
        )


def feed_object_prefix(feed_id: int) -> str:
    """Everything a feed owns in the bucket, for a delete that leaves nothing.

    Keyed by feed id and never by feed_name, so a rename moves no objects.
    """
    return f"feeds/{feed_id}/"


def object_key_for(feed_id: int, upload_id: str) -> str:
    return f"{feed_object_prefix(feed_id)}{upload_id}.zip"
