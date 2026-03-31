"""Per-consumer sliding-window rate limiter middleware."""

from __future__ import annotations

import hashlib
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Hard cap on tracked callers to prevent OOM under key-rotation attacks.
# When reached, the oldest inserted entry is evicted (FIFO).
_MAX_BUCKETS = 50_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding ``requests_per_minute`` per API key / IP.

    The caller key is a SHA-256 hash of the ``Authorization`` header value
    when present (e.g. ``Bearer <token>``), otherwise a hash of the client IP
    address.  Hashing prevents raw API keys from being stored as dict keys.

    Uses a per-caller sliding window — no reset spike at the boundary.

    NOTE: state is in-process only.  If ``GATEWAY_WORKERS > 1``, replace
    ``_buckets`` with a shared external store such as Redis.

    Health routes (``/health/…``) are exempt to allow load-balancer probes.
    """

    def __init__(self, app, *, requests_per_minute: int) -> None:
        super().__init__(app)
        self._limit = requests_per_minute
        self._window: float = 60.0
        # caller key → deque of monotonic request timestamps within the window.
        # Regular dict so we control membership (no defaultdict auto-recreate).
        self._buckets: dict[str, deque[float]] = {}

    def _get_auth_key(self, request: Request) -> str:
        client_host = request.client.host if request.client else "unknown"
        raw = request.headers.get("Authorization", client_host)
        return hashlib.sha256(raw.encode()).hexdigest()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path.startswith("/health"):
            return await call_next(request)

        key = self._get_auth_key(request)
        now = time.monotonic()
        cutoff = now - self._window

        bucket = self._buckets.get(key)
        if bucket is not None:
            # Trim timestamps that have left the sliding window.
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            # Free empty entries so stale callers don't linger in memory.
            if not bucket:
                del self._buckets[key]
                bucket = None

        if bucket is None:
            # Evict the oldest entry when at capacity to bound memory usage.
            if len(self._buckets) >= _MAX_BUCKETS:
                oldest_key = next(iter(self._buckets))
                del self._buckets[oldest_key]
            bucket = deque()
            self._buckets[key] = bucket

        if len(bucket) >= self._limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        bucket.append(now)
        return await call_next(request)
