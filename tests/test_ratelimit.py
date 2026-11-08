from gtfs_zone_wifi_ingest.ratelimit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit():
    limiter = RateLimiter(3, 60, FakeClock())
    assert [limiter.hit("a") for _ in range(3)] == [None, None, None]
    assert limiter.hit("a") == 60


def test_window_slides():
    clock = FakeClock()
    limiter = RateLimiter(2, 60, clock)
    limiter.hit("a")
    clock.now += 30
    limiter.hit("a")
    clock.now += 10
    assert limiter.hit("a") == 20
    clock.now += 20
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 30


def test_clients_are_separate():
    limiter = RateLimiter(1, 60, FakeClock())
    assert limiter.hit("a") is None
    assert limiter.hit("b") is None
    assert limiter.hit("a") is not None


def test_addresses_are_not_kept():
    limiter = RateLimiter(5, 60, FakeClock())
    limiter.hit("203.0.113.7")
    assert all(isinstance(k, bytes) and len(k) == 32 for k in limiter._hits)
    assert b"203.0.113.7" not in b"".join(limiter._hits)


def test_expired_clients_are_pruned():
    clock = FakeClock()
    limiter = RateLimiter(5, 60, clock)
    limiter.hit("a")
    clock.now += 61
    limiter.hit("b")
    assert len(limiter._hits) == 1
