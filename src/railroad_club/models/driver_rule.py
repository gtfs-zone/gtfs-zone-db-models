from datetime import time
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from railroad_club.models.driver import Driver


class DriverRule(SQLModel, table=True):
    __tablename__ = "driver_rule"

    id: int | None = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="driver.id")
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

    driver: "Driver" = Relationship(back_populates="rules")
