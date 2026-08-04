from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.feed import Feed
    from railroad_club.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FeedMember(SQLModel, table=True):
    """Someone other than the owner who may work on a feed.

    Members have the same access to a feed's contents as its owner. What they
    may *not* do is change who owns it, delete it, or manage this table.

    Modelled as a first-class row rather than a SQLModel ``link_model``
    many-to-many on purpose. A link_model would render in SQLAdmin as a
    multi-select of every user in the database (an enumeration leak), leave
    nowhere to record who added whom, and lazy-load into ``MissingGreenlet``
    under the async session. Membership is therefore only ever changed through
    routes that check permission server-side.
    """

    __tablename__ = "feed_member"
    __table_args__ = (UniqueConstraint("feed_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    feed_id: int = Field(foreign_key="feed.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    # Kept for the audit trail; nulled rather than cascading if that user goes.
    added_by_user_id: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    feed: "Feed" = Relationship(back_populates="members")
    user: "User" = Relationship(
        back_populates="memberships",
        sa_relationship_kwargs={"foreign_keys": "[FeedMember.user_id]"},
    )

    def __repr__(self) -> str:
        return f"FeedMember(feed_id={self.feed_id}, user_id={self.user_id})"
