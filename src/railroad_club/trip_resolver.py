from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from railroad_club.models.feed import Feed
from railroad_club.models.gtfs_static import GtfsStaticFeed
from railroad_club.models.tracker import Tracker
from railroad_club.models.tracker_rule import TrackerRule

_WEEKDAY_COLS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def resolve_tracker_trip(tracker_id: str, session: Session) -> str | None:
    """
    Return the trip_id for a tracker based on its active schedule rule, or None.

    Evaluation is done in the feed's GTFS timezone. If no timezone is available
    (feed has no loaded GtfsStaticFeed), returns None.
    Last-created rule wins when multiple rules overlap.
    """
    row = session.exec(
        select(Tracker, Feed, GtfsStaticFeed)
        .join(Feed, Tracker.feed_id == Feed.id)
        .join(
            GtfsStaticFeed, Feed.gtfs_static_feed_id == GtfsStaticFeed.id, isouter=True
        )
        .where(Tracker.id == tracker_id)
    ).first()

    if row is None:
        return None

    tracker, _feed, static_feed = row

    if static_feed is None or static_feed.timezone is None:
        return None

    now = datetime.now(ZoneInfo(static_feed.timezone))
    day_col = _WEEKDAY_COLS[now.weekday()]
    current_time = now.time().replace(tzinfo=None)

    rules = session.exec(
        select(TrackerRule)
        .where(TrackerRule.tracker_id == tracker.id)
        .where(getattr(TrackerRule, day_col) == True)  # noqa: E712
        .where(TrackerRule.start_time <= current_time)
        .where(TrackerRule.end_time > current_time)
        .order_by(TrackerRule.id.desc())
    ).all()

    return rules[0].trip_id if rules else None
