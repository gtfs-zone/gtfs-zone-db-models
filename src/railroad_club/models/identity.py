from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Identity(SQLModel, table=True):
    """One way of signing in as a :class:`User`.

    A person may hold several — GitHub and Google, say — and all of them point
    at the same ``user_id``. That is the whole point: the credential is not the
    identity. ``(provider, provider_subject)`` is what an OIDC login resolves
    against, and it is unique across the table.
    """

    __table_args__ = (UniqueConstraint("provider", "provider_subject"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    provider: str
    provider_subject: str
    # Not unique, deliberately: two identities legitimately carry one address —
    # that is exactly the case account linking exists to handle.
    email: str | None = Field(default=None, index=True)
    email_verified: bool = False
    linked_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user: "User" = Relationship(back_populates="identities")

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_subject}"

    def __repr__(self) -> str:
        return (
            f"Identity(id={self.id}, user_id={self.user_id}, "
            f"provider={self.provider!r}, subject={self.provider_subject!r})"
        )
