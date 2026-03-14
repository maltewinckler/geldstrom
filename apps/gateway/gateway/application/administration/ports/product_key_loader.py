"""Current product key loader port."""

from __future__ import annotations

from typing import Protocol


class CurrentProductKeyLoader(Protocol):
    """Loads the decrypted current product key into runtime memory."""

    async def load_current(self, current_key: str | None) -> None: ...
