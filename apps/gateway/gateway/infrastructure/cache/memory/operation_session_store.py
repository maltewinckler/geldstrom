"""In-memory runtime store for pending decoupled banking operations."""

from __future__ import annotations

import asyncio
from datetime import datetime

from gateway.application.common import InternalError
from gateway.domain.banking_gateway import (
    OperationSessionStore,
    OperationStatus,
    PendingOperationSession,
)


class InMemoryOperationSessionStore(OperationSessionStore):
    """Stores pending operation sessions in a bounded in-memory dictionary."""

    def __init__(self, *, max_sessions: int = 10_000) -> None:
        self._max_sessions = max_sessions
        self._sessions: dict[str, PendingOperationSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: PendingOperationSession) -> None:
        async with self._lock:
            if (
                session.operation_id not in self._sessions
                and len(self._sessions) >= self._max_sessions
            ):
                raise InternalError("The pending operation store is at capacity")
            self._sessions[session.operation_id] = session

    async def get(self, operation_id: str) -> PendingOperationSession | None:
        async with self._lock:
            return self._sessions.get(operation_id)

    async def update(self, session: PendingOperationSession) -> None:
        async with self._lock:
            self._sessions[session.operation_id] = session

    async def delete(self, operation_id: str) -> None:
        async with self._lock:
            self._sessions.pop(operation_id, None)

    async def expire_stale(self, now: datetime) -> int:
        _terminal = {
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.EXPIRED,
        }
        async with self._lock:
            stale_operation_ids = [
                operation_id
                for operation_id, session in self._sessions.items()
                if session.expires_at <= now and session.status in _terminal
            ]
            for operation_id in stale_operation_ids:
                self._sessions.pop(operation_id, None)
            return len(stale_operation_ids)

    async def list_all(self) -> list[PendingOperationSession]:
        async with self._lock:
            return list(self._sessions.values())
