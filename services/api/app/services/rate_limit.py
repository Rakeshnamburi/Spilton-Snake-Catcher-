import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Small-process fallback limiter; use Redis when running multiple API instances."""

    def __init__(self):
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> int | None:
        """Return retry-after seconds when denied, otherwise ``None``."""

        now = time.monotonic()
        with self._lock:
            events = self._buckets[key]
            while events and now - events[0] >= window_seconds:
                events.popleft()
            if len(events) >= limit:
                return max(1, int(window_seconds - (now - events[0])) + 1)
            events.append(now)
        return None

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = SlidingWindowRateLimiter()
