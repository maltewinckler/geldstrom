"""Extended session store port for the background resume worker."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway import (
    OperationSessionStore,
    PendingOperationSession,
)


class PendingOperationRuntimeStore(OperationSessionStore, Protocol):
    """Session store contract needed by the background resume worker."""

    async def list_all(self) -> list[PendingOperationSession]: ...
