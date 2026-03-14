"""Internal product key provider abstraction for banking use cases."""

from __future__ import annotations

from typing import Protocol


class CurrentProductKeyProvider(Protocol):
    """Returns the current decrypted product key for connector calls."""

    async def require_current(self) -> str:
        """Return the current plaintext product key or raise when unavailable."""
