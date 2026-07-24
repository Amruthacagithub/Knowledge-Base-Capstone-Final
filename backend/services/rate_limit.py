"""Small concurrency-safe sliding-window limiter for a single API process."""
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


MAX_RATE_LIMIT_KEYS = 10_000


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        key: str,
        limit: int,
        *,
        window_seconds: int = 60,
        now: float | None = None,
    ) -> RateLimitDecision:
        timestamp = monotonic() if now is None else now
        cutoff = timestamp - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - timestamp) + 1)
                return RateLimitDecision(False, retry_after)
            events.append(timestamp)
            if len(self._events) > MAX_RATE_LIMIT_KEYS:
                self._drop_empty_keys(cutoff)
            return RateLimitDecision(True, 0)

    def _drop_empty_keys(self, cutoff: float) -> None:
        stale_keys = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                stale_keys.append(key)
        for key in stale_keys:
            del self._events[key]


rate_limiter = SlidingWindowRateLimiter()