"""S3-compatible object storage, shared by cafe-car and schedule-foamer.

Both apps need the identical client: cafe-car writes an uploaded GTFS zip and
serves it back, schedule-foamer reads it to load the schedule. Neither should
own the other's copy, so it lives here beside the models the objects belong to.

Written against the S3 API rather than Garage's own, which is what the local
and deployed stacks run. A self-hoster who would rather point at AWS, R2 or B2
changes ``S3_ENDPOINT`` and nothing else.

boto3 is synchronous. Celery tasks call these methods directly; async callers
use ``AsyncObjectStore``, which is the same client with every call moved onto a
worker thread so it cannot block an event loop.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime


class ObjectStoreSettings(BaseSettings):
    # extra="ignore" because this owns a slice of an app's .env, not the whole
    # file. Forbidding extras would make every unrelated key in cafe-car's or
    # schedule-foamer's .env a ValidationError on the first store call.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Garage in compose and in k3s; any S3 endpoint elsewhere. Empty means the
    # store is not configured, and ObjectStore refuses to be built rather than
    # failing later on the first request.
    s3_endpoint: str = ""
    # One name, used by compose, by k3s and by both apps. Changing it here is
    # not enough on its own; it is also the bucket the deploy creates.
    s3_bucket: str = "gtfs-feeds"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    # Garage ignores the region but the S3 signature does not, so it has to be
    # some value and has to match what the bucket was created with.
    s3_region: str = "garage"


class ObjectStat(NamedTuple):
    key: str
    size_bytes: int
    last_modified: datetime
    etag: str


class ObjectStoreError(Exception):
    """The store rejected a call, or is not configured."""


class ObjectNotFound(ObjectStoreError):
    """No object at that key."""


class ObjectStore:
    """put / get / delete / delete_prefix / stat against one bucket."""

    def __init__(self, settings: ObjectStoreSettings) -> None:
        if not settings.s3_endpoint:
            raise ObjectStoreError(
                "S3_ENDPOINT is not set; object storage is unconfigured"
            )
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            # Garage serves one host for every bucket, so the bucket has to be
            # in the path. Virtual-host addressing would resolve
            # `gtfs-feeds.garage` and fail to connect.
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    def put(
        self, key: str, body: bytes, *, content_type: str = "application/zip"
    ) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=body, ContentType=content_type
            )
        except ClientError as exc:
            raise ObjectStoreError(f"put {key!r} failed: {exc}") from exc

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if _is_missing(exc):
                raise ObjectNotFound(key) from exc
            raise ObjectStoreError(f"get {key!r} failed: {exc}") from exc
        with response["Body"] as stream:
            return stream.read()

    def stat(self, key: str) -> ObjectStat:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if _is_missing(exc):
                raise ObjectNotFound(key) from exc
            raise ObjectStoreError(f"stat {key!r} failed: {exc}") from exc
        return ObjectStat(
            key=key,
            size_bytes=int(response["ContentLength"]),
            last_modified=response["LastModified"],
            etag=str(response["ETag"]).strip('"'),
        )

    def delete(self, key: str) -> None:
        """Remove an object. Deleting a key that is not there is not an error."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise ObjectStoreError(f"delete {key!r} failed: {exc}") from exc

    def delete_prefix(self, prefix: str) -> int:
        """Remove every object under a prefix, and return how many.

        This is what a feed delete calls. A prefix that matches nothing is a
        no-op, so a feed that never had an upload deletes cleanly.
        """
        deleted = 0
        # delete_objects takes 1000 keys at a time, and the listing is paged
        # anyway, so the batch is one page.
        for page in self._pages(prefix):
            keys = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if not keys:
                continue
            try:
                self._client.delete_objects(
                    Bucket=self._bucket, Delete={"Objects": keys, "Quiet": True}
                )
            except ClientError as exc:
                raise ObjectStoreError(
                    f"delete_prefix {prefix!r} failed: {exc}"
                ) from exc
            deleted += len(keys)
        return deleted

    def list_prefix(self, prefix: str) -> list[str]:
        """Every key under a prefix. For checking what a feed is actually holding."""
        return [
            item["Key"]
            for page in self._pages(prefix)
            for item in page.get("Contents", [])
        ]

    def _pages(self, prefix: str) -> Iterator[dict]:
        paginator = self._client.get_paginator("list_objects_v2")
        try:
            yield from paginator.paginate(Bucket=self._bucket, Prefix=prefix)
        except ClientError as exc:
            raise ObjectStoreError(f"list {prefix!r} failed: {exc}") from exc


class AsyncObjectStore:
    """``ObjectStore`` with every call on a worker thread.

    boto3 has no async client, and cafe-car's request handlers are coroutines.
    A blocking put of a 30 MB zip on the event loop would stall every other
    request in flight, which is the whole reason this wrapper exists.
    """

    def __init__(self, store: ObjectStore) -> None:
        self._store = store

    @property
    def sync(self) -> ObjectStore:
        return self._store

    async def put(
        self, key: str, body: bytes, *, content_type: str = "application/zip"
    ) -> None:
        await asyncio.to_thread(self._store.put, key, body, content_type=content_type)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._store.get, key)

    async def stat(self, key: str) -> ObjectStat:
        return await asyncio.to_thread(self._store.stat, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._store.delete, key)

    async def delete_prefix(self, prefix: str) -> int:
        return await asyncio.to_thread(self._store.delete_prefix, prefix)

    async def list_prefix(self, prefix: str) -> list[str]:
        return await asyncio.to_thread(self._store.list_prefix, prefix)


def _is_missing(exc: ClientError) -> bool:
    """Whether a ClientError is a 404 rather than a real failure.

    S3 answers a missing key with NoSuchKey on GET and a bare 404 with no error
    code on HEAD, so the status is checked as well as the code.
    """
    error = exc.response.get("Error", {})
    if error.get("Code") in ("NoSuchKey", "404", "NotFound"):
        return True
    return exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404


@lru_cache
def get_object_store() -> ObjectStore:
    """The process-wide store client.

    Built on first use, not at import: a worker that starts before Garage is
    reachable must not die, and a process that never touches an object should
    not need the store configured at all.
    """
    return ObjectStore(ObjectStoreSettings())


@lru_cache
def get_async_object_store() -> AsyncObjectStore:
    return AsyncObjectStore(get_object_store())
