from datetime import time
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.tracker import Tracker


class TrackerRule(SQLModel, table=True):
    __tablename__ = "tracker_rule"

    id: int | None = Field(default=None, primary_key=True)
    tracker_id: str = Field(foreign_key="tracker.id")
    trip_id: str = Field(max_length=256)
    monday: bool = Field(default=False)
    tuesday: bool = Field(default=False)
    wednesday: bool = Field(default=False)
    thursday: bool = Field(default=False)
    friday: bool = Field(default=False)
    saturday: bool = Field(default=False)
    sunday: bool = Field(default=False)
    start_time: time
    end_time: time

    tracker: "Tracker" = Relationship(back_populates="rules")
