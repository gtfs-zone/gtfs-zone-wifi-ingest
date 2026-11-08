import asyncio
from datetime import UTC, datetime

from conftest import keys

from gtfs_zone_wifi_ingest.store import marker_key, raw_key

SESSION = "3f6c2a8e-1b4d-4c7a-9e2f-5a6b7c8d9e0f"


def test_keys():
    at = datetime(2026, 1, 2, 23, 59, tzinfo=UTC)
    assert raw_key(1, SESSION, at) == f"raw/v1/2026/01/02/{SESSION}.json"
    assert marker_key(SESSION) == f"ids/{SESSION}"


def test_concurrent_duplicates_store_once(store, s3):
    async def run():
        return await asyncio.gather(*(store.put(1, SESSION, b"{}") for _ in range(5)))

    assert sorted(asyncio.run(run())) == [False, False, False, False, True]
    assert keys(s3) == [f"ids/{SESSION}", f"raw/v1/2026/11/08/{SESSION}.json"]
    assert store._locks == {}
