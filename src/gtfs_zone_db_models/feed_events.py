"""The per-feed event channel, named once so three repos agree on it.

schedule-foamer publishes; cafe-car subscribes and forwards each payload to
yard-master over SSE. Nothing here opens a Redis connection: every repo already
has its own client and its own settings, and what has to be shared is the
channel name and the payload shape, not the transport.

Redis pub/sub is global rather than scoped to a database number, so a publisher
on the Celery broker's db and a subscriber on cafe-car's would reach each other
even when the two disagree. They are pointed at the same db anyway, because
depending on that is the kind of thing nobody remembers a year later.

Every payload is a JSON object with a ``type``. cafe-car forwards the bytes
without parsing them, so adding an event type is a publisher change and a
client change with no server change in between. A payload must therefore be
JSON with no literal newline in it, which ``json.dumps`` guarantees and which
the SSE framing depends on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from gtfs_zone_db_models.models.gtfs_static import GtfsStaticFeed

# Where a feed's static load got to. Payload: ``{"type": "load", "load": {...}}``
# with ``load`` null for a feed the loader has never touched, which is not the
# same as pending and must not be shown as it.
EVENT_LOAD = "load"

# One vehicle's current fix. Payload: ``{"type": "position", "vehicle": {...}}``
# where ``vehicle`` is already in the camelCase GTFS-RT shape the map reads, so
# a client stores it without a translation layer. The builder lives in cafe-car
# next to the ``vehicle:*`` record it is built from.
EVENT_POSITION = "position"


def feed_channel(feed_id: int) -> str:
    """The pub/sub channel carrying one feed's events."""
    return f"feed:{feed_id}:events"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def load_event(static: GtfsStaticFeed | None) -> dict[str, Any]:
    """A ``load`` payload, mirroring cafe-car's ``LoadStatusOut``.

    Built from the row rather than from the task's local variables so what is
    pushed is what a later ``GET /api/feeds/{id}`` would answer. ``None`` is a
    feed with no ``gtfs_static_feed`` row at all.
    """
    if static is None:
        return {"type": EVENT_LOAD, "load": None}
    return {
        "type": EVENT_LOAD,
        "load": {
            "status": str(static.status),
            "error_message": static.error_message,
            "timezone": static.timezone,
            "last_loaded_at": _iso(static.last_loaded_at),
            "started_at": _iso(static.started_at),
            "next_retry_at": _iso(static.next_retry_at),
        },
    }


def position_event(vehicle: dict[str, Any]) -> dict[str, Any]:
    """Envelope one already-GTFS-RT-shaped vehicle as a ``position`` payload."""
    return {"type": EVENT_POSITION, "vehicle": vehicle}
