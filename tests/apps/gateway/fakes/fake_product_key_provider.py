"""In-memory fake current product key provider for application tests."""

from __future__ import annotations

from gateway.application.common import InternalError


class FakeProductKeyProvider:
    """Stores the current decrypted product key in memory."""

    def __init__(self, current_key: str | None = None) -> None:
        self._current_key = current_key

    async def require_current(self) -> str:
        if self._current_key is None:
            raise InternalError("No current product key is loaded")
        return self._current_key

    async def set_current(self, current_key: str | None) -> None:
        self._current_key = current_key

    async def load_current(self, current_key: str | None) -> None:
        self._current_key = current_key
