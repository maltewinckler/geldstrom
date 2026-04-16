"""Redis-backed operation session store."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from gateway.domain.banking_gateway import (
    BankProtocol,
    OperationSessionStore,
    OperationStatus,
    OperationType,
    PendingOperationSession,
)


def _serialize_session(session: PendingOperationSession) -> str:
    """Encode a session to a JSON string for Redis storage."""
    payload: dict[str, Any] = {
        "operation_id": session.operation_id,
        "consumer_id": str(session.consumer_id),
        "protocol": session.protocol.value,
        "operation_type": session.operation_type.value,
        "session_state": session.session_state.hex() if session.session_state else None,
        "status": session.status.value,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "last_polled_at": session.last_polled_at.isoformat()
        if session.last_polled_at
        else None,
        "result_payload": session.result_payload,
        "failure_reason": session.failure_reason,
    }
    return json.dumps(payload, separators=(",", ":"))


def _deserialize_session(data: str) -> PendingOperationSession:
    """Decode a JSON string from Redis into a PendingOperationSession."""
    parsed = json.loads(data)
    return PendingOperationSession(
        operation_id=parsed["operation_id"],
        consumer_id=UUID(parsed["consumer_id"]),
        protocol=BankProtocol(parsed["protocol"]),
        operation_type=OperationType(parsed["operation_type"]),
        session_state=bytes.fromhex(parsed["session_state"])
        if parsed["session_state"]
        else None,
        status=OperationStatus(parsed["status"]),
        created_at=datetime.fromisoformat(parsed["created_at"]),
        expires_at=datetime.fromisoformat(parsed["expires_at"]),
        last_polled_at=datetime.fromisoformat(parsed["last_polled_at"])
        if parsed["last_polled_at"]
        else None,
        result_payload=parsed.get("result_payload"),
        failure_reason=parsed.get("failure_reason"),
    )


def _key(operation_id: str) -> str:
    return f"ops:{operation_id}"


class RedisOperationSessionStore(OperationSessionStore):
    """Stores pending operation sessions in Redis with auto-expiry via TTL."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def create(self, session: PendingOperationSession) -> None:
        key = _key(session.operation_id)
        value = _serialize_session(session)
        ttl = self._ttl_seconds(session)
        if ttl > 0:
            await self._redis.setex(key, ttl, value)
        else:
            await self._redis.set(key, value)

    async def get(self, operation_id: str) -> PendingOperationSession | None:
        data = await self._redis.get(_key(operation_id))
        if data is None:
            return None
        return _deserialize_session(data if isinstance(data, str) else data.decode())

    async def update(self, session: PendingOperationSession) -> None:
        # Same as create - overwrite with refreshed TTL
        await self.create(session)

    async def delete(self, operation_id: str) -> None:
        await self._redis.delete(_key(operation_id))

    async def expire_stale(self, now: datetime) -> int:
        # Redis TTL handles automatic expiry, but we still need to clean up
        # terminal sessions whose TTL hasn't elapsed yet.
        _terminal = {
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.EXPIRED,
        }
        removed = 0
        async for key in self._redis.scan_iter(match="ops:*", count=100):
            data = await self._redis.get(key)
            if data is None:
                continue
            session = _deserialize_session(
                data if isinstance(data, str) else data.decode()
            )
            if session.expires_at <= now and session.status in _terminal:
                await self._redis.delete(key)
                removed += 1
        return removed

    async def list_all(self) -> list[PendingOperationSession]:
        sessions: list[PendingOperationSession] = []
        async for key in self._redis.scan_iter(match="ops:*", count=100):
            data = await self._redis.get(key)
            if data is None:
                continue
            sessions.append(
                _deserialize_session(data if isinstance(data, str) else data.decode())
            )
        return sessions

    @staticmethod
    def _ttl_seconds(session: PendingOperationSession) -> int:
        """Compute Redis key TTL from the session's expires_at.

        Adds a 60-second grace period so the application layer can still read
        a recently-expired session before Redis evicts it.
        """
        from datetime import UTC

        delta = session.expires_at - datetime.now(UTC)
        return max(int(delta.total_seconds()) + 60, 60)
