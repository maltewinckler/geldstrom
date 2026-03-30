"""Time and identifier provider abstractions for application use cases."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol


class IdProvider(Protocol):
    """Provides stable timestamps and operation identifiers to use cases."""

    def new_operation_id(self) -> str: ...

    def now(self) -> datetime: ...


def cap_session_expires_at(
    result_expires_at: datetime | None, now: datetime, ttl_seconds: int
) -> datetime:
    """Apply the gateway TTL cap: session lives at most ttl_seconds from now."""
    max_expires_at = now + timedelta(seconds=ttl_seconds)
    if result_expires_at is None:
        return max_expires_at
    return min(result_expires_at, max_expires_at)
