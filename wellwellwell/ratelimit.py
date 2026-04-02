from __future__ import annotations

import threading
import time


class RateLimiter:
    """Sliding-window rate limiter. Thread-safe."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            cutoff = now - self._window_seconds
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            if len(self._timestamps) >= self._max_calls:
                return False
            self._timestamps.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._timestamps.clear()

    @property
    def remaining(self) -> int:
        now = time.monotonic()
        with self._lock:
            cutoff = now - self._window_seconds
            active = sum(1 for t in self._timestamps if t > cutoff)
            return max(0, self._max_calls - active)


# Shared limiter for manual collections (5 per hour). The auto-collector resets it.
collect_limiter = RateLimiter(max_calls=5, window_seconds=3600)

# Rate limiter for failed password attempts on admin endpoints.
auth_fail_limiter = RateLimiter(max_calls=10, window_seconds=3600)
