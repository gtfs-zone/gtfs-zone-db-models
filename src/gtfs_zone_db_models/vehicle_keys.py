"""The Redis keyspace for live vehicles and trip updates.

Every producer and the serving side derive these strings from here. Two repos
deriving them independently is how ``vehicle:*`` came to mean a device in one
writer and a trip instance in another.

**A vehicle's identity is ``(tracker_id, vehicle_id)``.** ``trip_id`` and
``start_date`` live in the record as data, never in the key: a vehicle that
finishes one trip and starts another overwrites its own record instead of
leaving the old one to live out its TTL beside the new one.

**A tracker id never contains a colon**, which ``Tracker.validate_id``
enforces where ids are born. Nothing here re-checks it.

That is what the encoding rests on. Keys are built and split on the *first*
colon, so exactly one of the two segments may contain colons, and it has to be
``vehicle_id``: Amtrak's is ``449:20260921``. Were an id to carry one, the
encoding would stop being injective - ``("a:b", "c")`` and ``("a", "b:c")``
both give ``a:b:c`` - and two vehicles would share a record.
"""

from __future__ import annotations

VEHICLE_PREFIX = "vehicle:"
TRIP_UPDATE_PREFIX = "trip_update:"


def vehicle_key(tracker_id: str, vehicle_id: str | None) -> str:
    """The identity of one vehicle: a tracker, plus which vehicle on it.

    A producer with no per-vehicle id - a Traccar device is one tracker, one
    vehicle - gets the bare tracker id. This is the Redis key without its
    ``vehicle:`` prefix, so the same string addresses a record and a map
    feature.
    """
    return f"{tracker_id}:{vehicle_id}" if vehicle_id else tracker_id


def redis_key(tracker_id: str, vehicle_id: str | None) -> str:
    """Where one vehicle's record lives."""
    return f"{VEHICLE_PREFIX}{vehicle_key(tracker_id, vehicle_id)}"


def split_vehicle_key(key: str) -> tuple[str, str | None]:
    """Take a key or a ``vehicle:``-prefixed key back to its two parts.

    Splits on the first colon only, so a colon-bearing ``vehicle_id`` survives
    the round trip.
    """
    if key.startswith(VEHICLE_PREFIX):
        key = key[len(VEHICLE_PREFIX) :]
    tracker_id, _, vehicle_id = key.partition(":")
    return tracker_id, vehicle_id or None


def trip_update_key(
    tracker_id: str, trip_id: str, start_date: str | None = None
) -> str:
    """Where one trip's predictions live.

    Scoped by tracker because ``trip_id`` is only unique within a feed's GTFS:
    two feeds both numbering a trip ``"1"`` would otherwise overwrite each
    other. ``start_date`` separates concurrent instances of one daily trip.
    """
    slug = f"{trip_id}:{start_date}" if start_date else trip_id
    return f"{TRIP_UPDATE_PREFIX}{tracker_id}:{slug}"
