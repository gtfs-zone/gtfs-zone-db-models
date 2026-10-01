"""Which trip a tracker is running right now.

A rule's **service date** is the date its window starts in feed-local time, and
that date is the trip's GTFS-RT ``start_date``. A window that crosses midnight
keeps the earlier date for its whole run, which is why two service days are
evaluated for every fix: at 00:30 on Tuesday a 23:00-01:00 Monday rule is still
the live one, and Monday is the date the rest of the pipeline must agree on.

Times are seconds since service midnight, GTFS-shaped, so that 23:00-01:00 rule
is stored as 82800-90000 and needs no special case beyond the offset.
"""

from datetime import date, datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from gtfs_zone_db_models.models.feed import Feed
from gtfs_zone_db_models.models.gtfs_static import GtfsStaticFeed
from gtfs_zone_db_models.models.tracker import Tracker
from gtfs_zone_db_models.models.tracker_rule import (
    ExceptionType,
    TrackerRule,
    TrackerRuleException,
)

SECONDS_PER_DAY = 86400

_WEEKDAY_COLS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


class ResolvedTrip(NamedTuple):
    """Which tracker this is, what it is running, and which service day's run.

    ``trip_id`` and ``service_date`` are None together when the tracker exists
    but no rule places it on a trip right now. That is a tracker with a fix and
    no assignment, which is a thing to draw on a map rather than an error, so it
    is deliberately not the same answer as "no such tracker".
    """

    tracker_id: str
    trip_id: str | None
    service_date: date | None


def rule_applies_on(
    rule: TrackerRule, service_date: date, exceptions: dict[date, str]
) -> bool:
    """Whether a rule runs on a service date, exceptions applied.

    ``added`` overrides both the weekday flags and the date range's absence of
    that day; it does not override the range itself, so a date outside
    ``start_date``/``end_date`` never runs.
    """
    if service_date < rule.start_date:
        return False
    if rule.end_date is not None and service_date > rule.end_date:
        return False
    override = exceptions.get(service_date)
    if override == ExceptionType.removed:
        return False
    if override == ExceptionType.added:
        return True
    return bool(getattr(rule, _WEEKDAY_COLS[service_date.weekday()]))


def _load_exceptions(
    session: Session, rule_ids: list[int]
) -> dict[int, dict[date, str]]:
    if not rule_ids:
        return {}
    rows = session.exec(
        select(TrackerRuleException).where(TrackerRuleException.rule_id.in_(rule_ids))
    ).all()
    by_rule: dict[int, dict[date, str]] = {}
    for row in rows:
        by_rule.setdefault(row.rule_id, {})[row.date] = row.exception_type
    return by_rule


def resolve_tracker_trip(device_key: str, session: Session) -> ResolvedTrip | None:
    """Resolve a Traccar ``uniqueId`` to its tracker and the trip it is running.

    None means there is no such tracker. A tracker with no trip comes back with
    ``trip_id`` and ``service_date`` None, so a caller can still identify and
    place it.

    Evaluation is in the feed's GTFS timezone. A feed with no loaded
    ``GtfsStaticFeed``, or one with no timezone, yields no trip: there is no
    safe answer about *which* trip without knowing what local time means for
    that feed, and guessing one is worse than reporting none.

    Later service dates win, then the last-created rule, so a >24h window that
    matches on both evaluated days reports the run that started most recently.
    """
    row = session.exec(
        select(Tracker, Feed, GtfsStaticFeed)
        .join(Feed, Tracker.feed_id == Feed.id)
        .join(
            GtfsStaticFeed, Feed.gtfs_static_feed_id == GtfsStaticFeed.id, isouter=True
        )
        .where(Tracker.device_key == device_key)
    ).first()

    if row is None:
        return None

    tracker, _feed, static_feed = row

    if static_feed is None or static_feed.timezone is None:
        return ResolvedTrip(tracker.id, None, None)

    tz = ZoneInfo(static_feed.timezone)
    now = datetime.now(tz)
    today = now.date()

    rules = session.exec(
        select(TrackerRule).where(TrackerRule.tracker_id == tracker.id)
    ).all()
    exceptions = _load_exceptions(session, [r.id for r in rules if r.id is not None])

    best = ResolvedTrip(tracker.id, None, None)
    best_key: tuple[date, int] | None = None
    for days_back in (1, 0):
        service_date = today - timedelta(days=days_back)
        # Built from the date rather than by subtracting a day from today's
        # midnight, so the offset stays right across a DST transition.
        service_midnight = datetime.combine(service_date, time.min, tzinfo=tz)
        offset = int((now - service_midnight).total_seconds())
        for rule in rules:
            if not (rule.start_time <= offset < rule.end_time):
                continue
            if not rule_applies_on(rule, service_date, exceptions.get(rule.id, {})):
                continue
            # Later service date first, then the last-created rule.
            key = (service_date, rule.id)
            if best_key is None or key > best_key:
                best_key = key
                best = ResolvedTrip(tracker.id, rule.trip_id, service_date)

    return best


class Assignment(NamedTuple):
    """One rule occurring on one service date."""

    rule_id: int
    tracker_id: str
    trip_id: str
    service_date: date
    start_time: int
    end_time: int


def expand_rules(
    rules: list[TrackerRule],
    exceptions: dict[int, dict[date, str]],
    start: date,
    end: date,
) -> list[Assignment]:
    """Every occurrence of these rules between two service dates, inclusive.

    Pure, so the caller owns the query and therefore the access scoping. Dates
    are service dates, meaning a window that runs past midnight is reported on
    the day it started, with an ``end_time`` past 86400 rather than a second
    entry on the following day.
    """
    out: list[Assignment] = []
    day = start
    while day <= end:
        for rule in rules:
            if rule_applies_on(rule, day, exceptions.get(rule.id, {})):
                out.append(
                    Assignment(
                        rule_id=rule.id,
                        tracker_id=rule.tracker_id,
                        trip_id=rule.trip_id,
                        service_date=day,
                        start_time=rule.start_time,
                        end_time=rule.end_time,
                    )
                )
        day += timedelta(days=1)
    out.sort(key=lambda a: (a.service_date, a.start_time, a.rule_id))
    return out
