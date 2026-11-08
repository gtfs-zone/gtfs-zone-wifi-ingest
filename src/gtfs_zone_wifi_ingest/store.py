"""Raw session storage in the wifi-raw bucket."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import obstore

if TYPE_CHECKING:
    from collections.abc import Callable

    from obstore.store import ObjectStore

    from gtfs_zone_wifi_ingest.config import S3Settings

_JSON = {"Content-Type": "application/json"}
_TEXT = {"Content-Type": "text/plain"}


def s3_store(s3: S3Settings) -> ObjectStore:
    from obstore.store import S3Store

    return S3Store(
        s3.bucket,
        endpoint=s3.endpoint,
        region=s3.region,
        access_key_id=s3.access_key,
        secret_access_key=s3.secret_key,
        virtual_hosted_style_request=False,
        client_options={
            "allow_http": s3.endpoint.startswith("http://"),
            "timeout": "30s",
        },
    )


def raw_key(schema_version: int, session_id: str, at: datetime) -> str:
    return f"raw/v{schema_version}/{at:%Y/%m/%d}/{session_id}.json"


def marker_key(session_id: str) -> str:
    return f"ids/{session_id}"


async def _exists(store: ObjectStore, key: str) -> bool:
    try:
        await obstore.head_async(store, key)
    except FileNotFoundError:
        return False
    return True


class SessionStore:
    """Writes each session once, keyed by session_id.

    The raw key is dated by upload time, so `ids/<session_id>` holds the raw
    key and is how a later duplicate is found. The raw object is written
    before its marker, and a marker whose raw object is missing is repaired.
    """

    def __init__(
        self,
        store: ObjectStore,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.clock = clock
        # session_id -> lock and the number of requests holding or awaiting it
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}

    async def put(self, schema_version: int, session_id: str, body: bytes) -> bool:
        """Stores `body`; True if new, False if session_id was already stored."""
        lock, users = self._locks.get(session_id, (asyncio.Lock(), 0))
        self._locks[session_id] = (lock, users + 1)
        try:
            async with lock:
                return await self._put(schema_version, session_id, body)
        finally:
            lock, users = self._locks[session_id]
            if users == 1:
                del self._locks[session_id]
            else:
                self._locks[session_id] = (lock, users - 1)

    async def _put(self, schema_version: int, session_id: str, body: bytes) -> bool:
        marker = marker_key(session_id)
        try:
            stored = await obstore.get_async(self.store, marker)
            key = bytes(await stored.bytes_async()).decode()
        except FileNotFoundError:
            key = None
        if key is not None:
            if not await _exists(self.store, key):
                await obstore.put_async(self.store, key, body, attributes=_JSON)
            return False
        key = raw_key(schema_version, session_id, self.clock())
        await obstore.put_async(self.store, key, body, attributes=_JSON)
        await obstore.put_async(self.store, marker, key.encode(), attributes=_TEXT)
        return True
