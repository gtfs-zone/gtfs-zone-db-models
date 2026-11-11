"""S3-compatible object storage, shared by rt-api and static-importer.

Both apps need the identical client: gtfs-zone-rt-api writes an uploaded GTFS
zip and serves it back, gtfs-zone-static-importer reads it to load the
schedule. Neither should own the other's copy, so it lives here beside the
models the objects belong to.

Written against the S3 API rather than Garage's own, which is what the local
and deployed stacks run. A self-hoster who would rather point at AWS, R2 or B2
changes ``S3_ENDPOINT`` and nothing else.

Built on obstore. Celery tasks call ``ObjectStore`` directly; async callers use
``AsyncObjectStore``, which makes the same calls through obstore's native async
API so they cannot block an event loop.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple

import obstore
from obstore.exceptions import BaseError
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from datetime import datetime

    from obstore.store import ObjectStore as Store

# Errors a store call can raise besides FileNotFoundError: obstore's own, and
# OSError for transport failures.
_STORE_ERRORS = (BaseError, OSError)


class ObjectStoreSettings(BaseSettings):
    # extra="ignore" because this owns a slice of an app's .env, not the whole
    # file. Forbidding extras would make every unrelated key in gtfs-zone-rt-api's or
    # gtfs-zone-static-importer's .env a ValidationError on the first store call.
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


def _attributes(content_type: str, cache_control: str | None) -> dict[str, str]:
    """The object metadata a put stores and the store later serves as headers."""
    attributes = {"Content-Type": content_type}
    if cache_control is not None:
        attributes["Cache-Control"] = cache_control
    return attributes


class ObjectStat(NamedTuple):
    key: str
    size_bytes: int
    last_modified: datetime
    etag: str


class ObjectStoreError(Exception):
    """The store rejected a call, or is not configured."""


class ObjectNotFound(ObjectStoreError):
    """No object at that key."""


def s3_store(settings: ObjectStoreSettings) -> Store:
    """An obstore S3Store for the settings' bucket."""
    from obstore.store import S3Store

    return S3Store(
        settings.s3_bucket,
        endpoint=settings.s3_endpoint,
        region=settings.s3_region,
        access_key_id=settings.s3_access_key,
        secret_access_key=settings.s3_secret_key,
        # Garage serves one host for every bucket, so the bucket has to be in
        # the path. Virtual-host addressing would resolve `gtfs-feeds.garage`
        # and fail to connect.
        virtual_hosted_style_request=False,
        client_options={
            "allow_http": settings.s3_endpoint.startswith("http://"),
            "timeout": "120s",
        },
    )


def _stat(key: str, meta: dict) -> ObjectStat:
    return ObjectStat(
        key=key,
        size_bytes=int(meta["size"]),
        last_modified=meta["last_modified"],
        etag=str(meta.get("e_tag") or "").strip('"'),
    )


class ObjectStore:
    """put / get / delete / delete_prefix / stat against one bucket.

    ``store`` replaces the S3 client, e.g. with obstore's ``MemoryStore`` in
    tests.
    """

    def __init__(
        self, settings: ObjectStoreSettings, store: Store | None = None
    ) -> None:
        if store is None and not settings.s3_endpoint:
            raise ObjectStoreError(
                "S3_ENDPOINT is not set; object storage is unconfigured"
            )
        self._bucket = settings.s3_bucket
        self._store = store if store is not None else s3_store(settings)

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def store(self) -> Store:
        return self._store

    def put(
        self,
        key: str,
        body: bytes,
        *,
        content_type: str = "application/zip",
        cache_control: str | None = None,
    ) -> None:
        try:
            # One PUT keeps the ETag an md5 of the body.
            obstore.put(
                self._store,
                key,
                body,
                use_multipart=False,
                attributes=_attributes(content_type, cache_control),
            )
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"put {key!r} failed: {exc}") from exc

    def get(self, key: str) -> bytes:
        try:
            return bytes(obstore.get(self._store, key).bytes())
        except FileNotFoundError as exc:
            raise ObjectNotFound(key) from exc
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"get {key!r} failed: {exc}") from exc

    def stat(self, key: str) -> ObjectStat:
        try:
            meta = obstore.head(self._store, key)
        except FileNotFoundError as exc:
            raise ObjectNotFound(key) from exc
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"stat {key!r} failed: {exc}") from exc
        return _stat(key, meta)

    def delete(self, key: str) -> None:
        """Remove an object. Deleting a key that is not there is not an error."""
        try:
            obstore.delete(self._store, key)
        except FileNotFoundError:
            pass
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"delete {key!r} failed: {exc}") from exc

    def delete_prefix(self, prefix: str) -> int:
        """Remove every object under a prefix, and return how many.

        This is what a feed delete calls. A prefix that matches nothing is a
        no-op, so a feed that never had an upload deletes cleanly.
        """
        keys = self.list_prefix(prefix)
        if not keys:
            return 0
        try:
            # obstore sends S3 bulk deletes of up to 1000 keys each.
            obstore.delete(self._store, keys)
        except FileNotFoundError:
            pass
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"delete_prefix {prefix!r} failed: {exc}") from exc
        return len(keys)

    def list_prefix(self, prefix: str) -> list[str]:
        """Every key under a prefix. For checking what a feed is actually holding."""
        try:
            return [
                meta["path"]
                for batch in obstore.list(self._store, prefix=prefix)
                for meta in batch
            ]
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"list {prefix!r} failed: {exc}") from exc


class AsyncObjectStore:
    """``ObjectStore`` over obstore's async calls.

    gtfs-zone-rt-api's request handlers are coroutines, and a blocking put of a
    30 MB zip on the event loop would stall every other request in flight.
    """

    def __init__(self, store: ObjectStore) -> None:
        self._store = store.store

    async def put(
        self,
        key: str,
        body: bytes,
        *,
        content_type: str = "application/zip",
        cache_control: str | None = None,
    ) -> None:
        try:
            await obstore.put_async(
                self._store,
                key,
                body,
                use_multipart=False,
                attributes=_attributes(content_type, cache_control),
            )
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"put {key!r} failed: {exc}") from exc

    async def get(self, key: str) -> bytes:
        try:
            result = await obstore.get_async(self._store, key)
            return bytes(await result.bytes_async())
        except FileNotFoundError as exc:
            raise ObjectNotFound(key) from exc
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"get {key!r} failed: {exc}") from exc

    async def stat(self, key: str) -> ObjectStat:
        try:
            meta = await obstore.head_async(self._store, key)
        except FileNotFoundError as exc:
            raise ObjectNotFound(key) from exc
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"stat {key!r} failed: {exc}") from exc
        return _stat(key, meta)

    async def delete(self, key: str) -> None:
        try:
            await obstore.delete_async(self._store, key)
        except FileNotFoundError:
            pass
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"delete {key!r} failed: {exc}") from exc

    async def delete_prefix(self, prefix: str) -> int:
        keys = await self.list_prefix(prefix)
        if not keys:
            return 0
        try:
            await obstore.delete_async(self._store, keys)
        except FileNotFoundError:
            pass
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"delete_prefix {prefix!r} failed: {exc}") from exc
        return len(keys)

    async def list_prefix(self, prefix: str) -> list[str]:
        try:
            return [
                meta["path"]
                async for batch in obstore.list(self._store, prefix=prefix)
                for meta in batch
            ]
        except _STORE_ERRORS as exc:
            raise ObjectStoreError(f"list {prefix!r} failed: {exc}") from exc


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
