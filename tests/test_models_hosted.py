"""The hosted-feed model: the key layout, and what is_hosted answers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from railroad_club.models import (
    Feed,
    FeedSourceKind,
    GtfsUpload,
    feed_object_prefix,
    object_key_for,
)


def test_object_key_sits_under_the_feed_prefix():
    key = object_key_for(7, "deadbeef")
    assert key == "feeds/7/deadbeef.zip"
    assert key.startswith(feed_object_prefix(7))


def test_upload_id_is_generated_before_insert():
    upload = GtfsUpload(
        feed_id=1,
        object_key="feeds/1/x.zip",
        sha256="0" * 64,
        size_bytes=1,
        original_filename="gtfs.zip",
    )
    assert len(upload.id) == 32
    assert upload.uploaded_at is not None


def test_a_new_feed_is_url_sourced():
    feed = Feed(
        feed_name="west", static_feed_url="https://example.com/g.zip", owner_id=1
    )
    assert feed.source_kind == FeedSourceKind.url
    assert not feed.is_hosted


def test_hosted_feed_needs_no_url():
    feed = Feed(feed_name="west", source_kind=FeedSourceKind.hosted, owner_id=1)
    assert feed.is_hosted
    assert feed.static_feed_url is None


# SQLModel skips validation on a table class's __init__, so the validators only
# fire through model_validate. That is the path an API payload takes.
def test_source_kind_is_closed():
    with pytest.raises(ValidationError):
        Feed.model_validate(
            {"feed_name": "west", "source_kind": "mirrored", "owner_id": 1}
        )


def test_a_url_that_is_not_a_url_is_still_rejected():
    with pytest.raises(ValidationError):
        Feed.model_validate(
            {"feed_name": "west", "static_feed_url": "not-a-url", "owner_id": 1}
        )


def test_a_null_url_passes_the_validator():
    feed = Feed.model_validate(
        {"feed_name": "west", "source_kind": "hosted", "owner_id": 1}
    )
    assert feed.static_feed_url is None
