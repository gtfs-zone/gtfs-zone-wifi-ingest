"""In-memory sliding-window rate limit per client."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class RateLimiter:
    """Allows `limit` hits per `window_s` seconds per client.

    Clients are keyed by an HMAC of the address under a per-process random
    key, so addresses are never kept.
    """

    def __init__(
        self,
        limit: int,
        window_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_s = window_s
        self.clock = clock
        self._key = secrets.token_bytes(32)
        self._hits: dict[bytes, deque[float]] = {}
        self._lock = threading.Lock()

    def _client(self, address: str) -> bytes:
        return hmac.digest(self._key, address.encode(), hashlib.sha256)

    def hit(self, address: str) -> float | None:
        """Records a hit; None if allowed, else seconds until the next slot."""
        client = self._client(address)
        now = self.clock()
        cutoff = now - self.window_s
        with self._lock:
            self._prune(cutoff)
            hits = self._hits.setdefault(client, deque())
            if len(hits) >= self.limit:
                return max(hits[0] - cutoff, 0.0)
            hits.append(now)
            return None

    def _prune(self, cutoff: float) -> None:
        for client in list(self._hits):
            hits = self._hits[client]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[client]
