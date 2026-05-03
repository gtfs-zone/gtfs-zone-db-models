from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from railroad_club.models.driver import Driver
from railroad_club.models.driver_rule import DriverRule
from railroad_club.models.feed import Feed
from railroad_club.models.gtfs_static import GtfsStaticFeed

_WEEKDAY_COLS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def resolve_driver_trip(username: str, session: Session) -> str | None:
    """
    Return the trip_id for a driver based on their active schedule rule, or None.

    Evaluation is done in the feed's GTFS timezone. If no timezone is available
    (feed has no loaded GtfsStaticFeed), returns None.
    Last-created rule wins when multiple rules overlap.
    """
    row = session.exec(
        select(Driver, Feed, GtfsStaticFeed)
        .join(Feed, Driver.feed_id == Feed.id)
        .join(
            GtfsStaticFeed, Feed.gtfs_static_feed_id == GtfsStaticFeed.id, isouter=True
        )
        .where(Driver.username == username)
    ).first()

    if row is None:
        return None

    driver, _feed, static_feed = row

    if static_feed is None or static_feed.timezone is None:
        return None

    now = datetime.now(ZoneInfo(static_feed.timezone))
    day_col = _WEEKDAY_COLS[now.weekday()]
    current_time = now.time().replace(tzinfo=None)

    rules = session.exec(
        select(DriverRule)
        .where(DriverRule.driver_id == driver.id)
        .where(getattr(DriverRule, day_col) == True)  # noqa: E712
        .where(DriverRule.start_time <= current_time)
        .where(DriverRule.end_time > current_time)
        .order_by(DriverRule.id.desc())
    ).all()

    return rules[0].trip_id if rules else None
