import re
from typing import TYPE_CHECKING, Optional

from pydantic import AnyHttpUrl, TypeAdapter, field_validator
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

from railroad_club.models.gtfs_upload import FeedSourceKind

if TYPE_CHECKING:
    from railroad_club.models.feed_invite import FeedInvite
    from railroad_club.models.feed_member import FeedMember
    from railroad_club.models.gtfs_static import GtfsStaticFeed
    from railroad_club.models.gtfs_upload import GtfsUpload
    from railroad_club.models.service_alert import ServiceAlert
    from railroad_club.models.tracker import Tracker
    from railroad_club.models.user import User

_url_validator = TypeAdapter(AnyHttpUrl)

_FEED_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")


class Feed(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    feed_name: str = Field(unique=True, index=True, max_length=64)
    # Where the schedule comes from. Every row that predates hosting is 'url',
    # which is exactly what it is.
    source_kind: str = Field(default=FeedSourceKind.url, max_length=16)
    # Required when source_kind is 'url', null when hosted. Nullable since
    # hosting: read it through `is_hosted` rather than testing it for None.
    static_feed_url: str | None = Field(default=None)
    owner_id: int = Field(foreign_key="user.id")
    gtfs_static_feed_id: int | None = Field(
        default=None, foreign_key="gtfs_static_feed.id"
    )
    # The upload the feed is currently serving, of however many it has kept.
    # `use_alter` because gtfs_upload.feed_id points back here: without it the
    # two CREATE TABLEs are a cycle neither can be first in.
    current_upload_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(32),
            ForeignKey(
                "gtfs_upload.id",
                use_alter=True,
                name="fk_feed_current_upload_id",
            ),
            nullable=True,
        ),
    )
    owner: "User" = Relationship(back_populates="feeds")
    members: list["FeedMember"] = Relationship(
        back_populates="feed", cascade_delete=True
    )
    invites: list["FeedInvite"] = Relationship(
        back_populates="feed", cascade_delete=True
    )
    trackers: list["Tracker"] = Relationship(back_populates="feed")
    alerts: list["ServiceAlert"] = Relationship(back_populates="feed")
    gtfs_static_feed: Optional["GtfsStaticFeed"] = Relationship()
    # Two paths join these tables, so both sides name the column they mean.
    uploads: list["GtfsUpload"] = Relationship(
        back_populates="feed",
        sa_relationship_kwargs={"foreign_keys": "[GtfsUpload.feed_id]"},
    )
    current_upload: Optional["GtfsUpload"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Feed.current_upload_id]"},
    )

    @property
    def is_hosted(self) -> bool:
        """Whether the schedule is ours to serve. No caller compares strings."""
        return self.source_kind == FeedSourceKind.hosted

    @field_validator("feed_name")
    @classmethod
    def validate_feed_name(cls, v: str) -> str:
        if not _FEED_NAME_RE.match(v):
            raise ValueError(
                "feed_name must start with a lowercase letter and contain only "
                "lowercase letters, digits, underscores, and hyphens (3-64 chars)"
            )
        return v

    @field_validator("source_kind")
    @classmethod
    def validate_source_kind(cls, v: str) -> str:
        if v not in tuple(FeedSourceKind):
            allowed = ", ".join(FeedSourceKind)
            raise ValueError(f"source_kind must be one of: {allowed}")
        return v

    @field_validator("static_feed_url")
    @classmethod
    def validate_static_feed_url(cls, v: str | None) -> str | None:
        # None is the hosted case. Whether that is legal for this row is a
        # question about source_kind, and the API answers it: a validator here
        # cannot see the other field on a partial update.
        if v is None:
            return None
        try:
            _url_validator.validate_python(v)
        except Exception:
            raise ValueError("Must be a valid http or https URL") from None
        return v

    def __str__(self) -> str:
        return self.feed_name

    def __repr__(self) -> str:
        return f"Feed(id={self.id}, feed_name={self.feed_name!r})"
