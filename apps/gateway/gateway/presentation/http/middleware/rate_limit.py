"""Per-consumer sliding-window rate limiter middleware."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding ``requests_per_minute`` per API key / IP.

    The caller key is the raw ``Authorization`` header value when present
    (e.g. ``Bearer <token>``), otherwise the client IP address.

    Uses a per-caller sliding window — no reset spike at the boundary.

    NOTE: state is in-process only.  If ``GATEWAY_WORKERS > 1``, replace
    ``_buckets`` with a shared external store such as Redis.

    Health routes (``/health/…``) are exempt to allow load-balancer probes.
    """

    def __init__(self, app, *, requests_per_minute: int) -> None:
        super().__init__(app)
        self._limit = requests_per_minute
        self._window: float = 60.0
        # caller key → deque of monotonic request timestamps within the window
        self._buckets: defaultdict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path.startswith("/health"):
            return await call_next(request)

        key = request.headers.get("Authorization") or (
            request.client.host if request.client else "unknown"
        )
        now = time.monotonic()
        bucket = self._buckets[key]
        cutoff = now - self._window

        # Trim timestamps that have left the sliding window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        # Opportunistically free empty buckets to bound memory usage
        if not bucket and key in self._buckets:
            del self._buckets[key]
            bucket = self._buckets[key]

        if len(bucket) >= self._limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        bucket.append(now)
        return await call_next(request)
