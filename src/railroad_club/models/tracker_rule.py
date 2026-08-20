from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.tracker import Tracker


class ExceptionType(StrEnum):
    added = "added"
    removed = "removed"


class TrackerRule(SQLModel, table=True):
    """When a tracker is running a given trip.

    ``start_time``/``end_time`` are seconds since service midnight, GTFS-shaped,
    so a window that crosses midnight is expressible: 23:00-01:00 is
    82800-90000. The weekday flags and the date range are tested against the
    rule's *service date*, which is the date its window starts in feed-local
    time, and that date is the trip's GTFS-RT ``start_date``.
    """

    __tablename__ = "tracker_rule"

    id: int | None = Field(default=None, primary_key=True)
    tracker_id: str = Field(foreign_key="tracker.id", index=True)
    trip_id: str = Field(max_length=256)
    monday: bool = Field(default=False)
    tuesday: bool = Field(default=False)
    wednesday: bool = Field(default=False)
    thursday: bool = Field(default=False)
    friday: bool = Field(default=False)
    saturday: bool = Field(default=False)
    sunday: bool = Field(default=False)
    # First service date the rule applies to.
    start_date: date
    # Last service date, inclusive. None is open-ended, not expired.
    end_date: date | None = Field(default=None)
    start_time: int
    end_time: int

    tracker: "Tracker" = Relationship(back_populates="rules")
    exceptions: list["TrackerRuleException"] = Relationship(
        back_populates="rule", cascade_delete=True
    )


class TrackerRuleException(SQLModel, table=True):
    """A single service date added to or removed from a rule.

    ``added`` makes the rule apply on a date its weekday flags exclude;
    ``removed`` cancels it on a date they include. Both are tested against the
    service date, never the wall-clock date of a fix.
    """

    __tablename__ = "tracker_rule_exception"
    __table_args__ = (UniqueConstraint("rule_id", "date"),)

    id: int | None = Field(default=None, primary_key=True)
    rule_id: int = Field(foreign_key="tracker_rule.id", index=True, ondelete="CASCADE")
    date: date
    exception_type: str = Field(max_length=16)

    rule: "TrackerRule" = Relationship(back_populates="exceptions")
