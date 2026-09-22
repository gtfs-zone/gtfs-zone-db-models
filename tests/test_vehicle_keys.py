"""The key derivation every producer and the serving side share.

The cases that matter are the ones that broke: a ``vehicle_id`` carrying
colons (Amtrak's ``train_num:start_date``), and an absent one (a Traccar
device, which is one vehicle per tracker).
"""

from __future__ import annotations

from railroad_club.vehicle_keys import (
    redis_key,
    split_vehicle_key,
    trip_update_key,
    vehicle_key,
)

TRACKER = "0c4f1e8a9b2d4c7e8f1a2b3c4d5e6f70"


def test_vehicle_key_joins_tracker_and_vehicle():
    assert vehicle_key(TRACKER, "bus-12") == f"{TRACKER}:bus-12"


def test_vehicle_key_without_vehicle_id_is_the_bare_tracker():
    assert vehicle_key(TRACKER, None) == TRACKER


def test_empty_vehicle_id_is_treated_as_absent():
    assert vehicle_key(TRACKER, "") == TRACKER


def test_redis_key_prefixes_the_vehicle_key():
    assert redis_key(TRACKER, "bus-12") == f"vehicle:{TRACKER}:bus-12"
    assert redis_key(TRACKER, None) == f"vehicle:{TRACKER}"


def test_colon_bearing_vehicle_id_survives_the_round_trip():
    key = redis_key(TRACKER, "449:20260921")
    assert split_vehicle_key(key) == (TRACKER, "449:20260921")


def test_split_accepts_an_unprefixed_key():
    assert split_vehicle_key(f"{TRACKER}:bus-12") == (TRACKER, "bus-12")


def test_split_of_a_bare_tracker_key_gives_no_vehicle_id():
    assert split_vehicle_key(f"vehicle:{TRACKER}") == (TRACKER, None)


def test_trip_update_key_is_scoped_by_tracker():
    assert trip_update_key(TRACKER, "trip-1") == f"trip_update:{TRACKER}:trip-1"


def test_trip_update_key_separates_instances_by_start_date():
    assert (
        trip_update_key(TRACKER, "trip-1", "20260921")
        == f"trip_update:{TRACKER}:trip-1:20260921"
    )
