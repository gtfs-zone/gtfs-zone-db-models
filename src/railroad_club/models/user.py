from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.feed import Feed
    from railroad_club.models.identity import Identity


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    """A person, independent of how they sign in.

    Credentials live in :class:`Identity` — one row per linked provider — so
    that signing in with GitHub or with Google lands on the same ``User``, and
    so that everything keyed on a ``user.id`` (feeds, memberships) survives a
    change of identity provider.
    """

    id: int | None = Field(default=None, primary_key=True)
    # Denormalised from the identities for display and for matching pending
    # feed invites; refreshed on login. Not authoritative, and not unique.
    primary_email: str | None = Field(default=None, index=True)
    display_name: str | None = None
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    identities: list["Identity"] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    feeds: list["Feed"] = Relationship(back_populates="owner")

    def __str__(self) -> str:
        return self.display_name or self.primary_email or f"user {self.id}"

    def __repr__(self) -> str:
        return f"User(id={self.id}, primary_email={self.primary_email!r})"
