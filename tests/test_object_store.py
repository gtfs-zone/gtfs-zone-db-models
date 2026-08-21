"""ObjectStore against moto's in-process S3.

Not a Garage container: the point of writing to the S3 API rather than Garage's
own is that any S3 implementation answers the same, so a fake that speaks S3 is
a fair test of this wrapper. Garage's own behaviour is the deploy's problem.
"""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from railroad_club.object_store import (
    ObjectNotFound,
    ObjectStore,
    ObjectStoreError,
    ObjectStoreSettings,
)

BUCKET = "test-feeds"


ENDPOINT = "http://s3.local"


@pytest.fixture
def store(monkeypatch):
    # moto matches requests by URL, and only recognises AWS hostnames unless
    # told otherwise. The endpoint is deliberately not an AWS one: this wrapper
    # points at Garage, and a test against s3.amazonaws.com would not exercise
    # the path addressing that requires.
    monkeypatch.setenv("MOTO_S3_CUSTOM_ENDPOINTS", ENDPOINT)
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield ObjectStore(
            ObjectStoreSettings(
                s3_endpoint=ENDPOINT,
                s3_bucket=BUCKET,
                s3_access_key="key",
                s3_secret_key="secret",
                s3_region="us-east-1",
            )
        )


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
