"""In-memory fake operation session store for application tests."""

from __future__ import annotations

from datetime import datetime

from gateway.domain.banking_gateway import OperationStatus, PendingOperationSession


class FakeOperationSessionStore:
    """Stores operation sessions in a mutable in-memory dictionary."""

    def __init__(self, sessions: list[PendingOperationSession] | None = None) -> None:
        self._sessions = {session.operation_id: session for session in sessions or []}

    async def create(self, session: PendingOperationSession) -> None:
        self._sessions[session.operation_id] = session

    async def get(self, operation_id: str) -> PendingOperationSession | None:
        return self._sessions.get(operation_id)

    async def update(self, session: PendingOperationSession) -> None:
        self._sessions[session.operation_id] = session

    async def delete(self, operation_id: str) -> None:
        self._sessions.pop(operation_id, None)

    async def expire_stale(self, now: datetime) -> int:
        _terminal = {
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.EXPIRED,
        }
        stale_operation_ids = [
            operation_id
            for operation_id, session in self._sessions.items()
            if session.expires_at <= now and session.status in _terminal
        ]
        for operation_id in stale_operation_ids:
            self._sessions.pop(operation_id, None)
        return len(stale_operation_ids)

    async def list_all(self) -> list[PendingOperationSession]:
        return list(self._sessions.values())
