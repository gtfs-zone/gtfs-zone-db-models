from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import field_validator
from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from gtfs_zone_db_models.models.feed import Feed


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FeedInvite(SQLModel, table=True):
    """A pending share for someone who has not signed in yet.

    Claimed on login when a *verified* address matches, which turns it into a
    :class:`FeedMember`. Matching on an unverified address would be an account
    takeover primitive, so ``email`` is only ever compared against verified
    identities.
    """

    __tablename__ = "feed_invite"

    id: int | None = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feed.id", index=True, ondelete="CASCADE")
    # Always stored lowercased so matching is case-insensitive without a
    # function index; see the validator below.
    email: str = Field(index=True)
    invited_by_user_id: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    claimed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    claimed_user_id: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )

    feed: "Feed" = Relationship(back_populates="invites")

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()

    def __repr__(self) -> str:
        return f"FeedInvite(feed_id={self.feed_id}, email={self.email!r})"
