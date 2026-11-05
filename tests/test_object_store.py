"""ObjectStore against obstore's in-memory store.

Not a Garage container: the point of writing to the S3 API rather than Garage's
own is that any S3 implementation answers the same, so an in-memory store is a
fair test of this wrapper. Garage's own behaviour is the deploy's problem.
"""

from __future__ import annotations

import asyncio

import pytest
from obstore.store import MemoryStore

from gtfs_zone_db_models.object_store import (
    AsyncObjectStore,
    ObjectNotFound,
    ObjectStore,
    ObjectStoreError,
    ObjectStoreSettings,
)

BUCKET = "test-feeds"


@pytest.fixture
def store():
    return ObjectStore(ObjectStoreSettings(s3_bucket=BUCKET), store=MemoryStore())


def test_unconfigured_endpoint_refuses_to_build():
    with pytest.raises(ObjectStoreError):
        ObjectStore(ObjectStoreSettings(s3_endpoint=""))


def test_put_then_get_round_trips(store):
    store.put("feeds/1/abc.zip", b"PK\x03\x04payload")
    assert store.get("feeds/1/abc.zip") == b"PK\x03\x04payload"


def test_get_missing_raises_not_found(store):
    with pytest.raises(ObjectNotFound):
        store.get("feeds/1/nope.zip")


def test_stat_reports_size_and_etag(store):
    store.put("feeds/1/abc.zip", b"0123456789")
    stat = store.stat("feeds/1/abc.zip")
    assert stat.size_bytes == 10
    assert stat.etag and '"' not in stat.etag
    assert stat.last_modified is not None


def test_stat_missing_raises_not_found(store):
    with pytest.raises(ObjectNotFound):
        store.stat("feeds/1/nope.zip")


def test_delete_is_idempotent(store):
    store.put("feeds/1/abc.zip", b"x")
    store.delete("feeds/1/abc.zip")
    store.delete("feeds/1/abc.zip")
    with pytest.raises(ObjectNotFound):
        store.get("feeds/1/abc.zip")


def test_delete_prefix_takes_one_feed_and_leaves_the_others(store):
    for key in ("feeds/1/a.zip", "feeds/1/b.zip", "feeds/2/c.zip"):
        store.put(key, b"x")

    assert store.delete_prefix("feeds/1/") == 2
    assert store.list_prefix("feeds/") == ["feeds/2/c.zip"]


def test_delete_prefix_of_nothing_is_not_an_error(store):
    assert store.delete_prefix("feeds/999/") == 0


def test_s3_store_builds_from_settings():
    store = ObjectStore(
        ObjectStoreSettings(s3_endpoint="http://garage:3900", s3_bucket=BUCKET)
    )
    assert store.bucket == BUCKET


def test_async_store_matches_the_sync_one(store):
    async_store = AsyncObjectStore(store)

    async def run():
        await async_store.put("feeds/1/a.zip", b"abc")
        await async_store.put("feeds/1/b.zip", b"d")
        assert await async_store.get("feeds/1/a.zip") == b"abc"
        assert (await async_store.stat("feeds/1/a.zip")).size_bytes == 3
        assert await async_store.list_prefix("feeds/1/") == [
            "feeds/1/a.zip",
            "feeds/1/b.zip",
        ]
        await async_store.delete("feeds/1/a.zip")
        await async_store.delete("feeds/1/a.zip")
        with pytest.raises(ObjectNotFound):
            await async_store.stat("feeds/1/a.zip")
        assert await async_store.delete_prefix("feeds/1/") == 1

    asyncio.run(run())
