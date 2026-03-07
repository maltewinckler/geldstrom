"""Redis-backed ChallengeRepository with Fernet encryption.

Implements the ChallengeRepository port using Redis for ephemeral storage.
PendingChallenge instances are serialized to JSON, encrypted with Fernet,
and stored with a TTL derived from SessionIdentity.expires_at.

Key pattern: gateway:challenge:{session_id}
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import redis.asyncio as aioredis
from cryptography.fernet import Fernet, InvalidToken

from gateway.domain.session.entities.pending_challenge import PendingChallenge
from gateway.domain.session.value_objects.session_identity import SessionIdentity

_KEY_PREFIX = "gateway:challenge:"


def _serialize(challenge: PendingChallenge) -> bytes:
    """Serialize PendingChallenge to JSON bytes, base64-encoding bytes fields."""
    data = challenge.model_dump(mode="python")
    data["dialog_state"] = base64.b64encode(data["dialog_state"]).decode()
    if data["media_data"] is not None:
        data["media_data"] = base64.b64encode(data["media_data"]).decode()
    data["identity"]["expires_at"] = data["identity"]["expires_at"].isoformat()
    return json.dumps(data).encode()


def _deserialize(raw: bytes) -> PendingChallenge:
    """Deserialize JSON bytes back to PendingChallenge, decoding base64 bytes fields."""
    data = json.loads(raw)
    data["dialog_state"] = base64.b64decode(data["dialog_state"])
    if data["media_data"] is not None:
        data["media_data"] = base64.b64decode(data["media_data"])
    return PendingChallenge.model_validate(data)


class RedisChallengeRepository:
    """Implements ChallengeRepository port using Redis with encrypted blobs."""

    def __init__(self, redis: aioredis.Redis, encryption_key: bytes) -> None:
        self._redis = redis
        self._fernet = Fernet(encryption_key)

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def save(self, challenge: PendingChallenge) -> None:
        """Serialize PendingChallenge → JSON → encrypt → Redis SET with TTL."""
        ttl_seconds = int(
            (challenge.identity.expires_at - datetime.now(UTC)).total_seconds()
        )
        if ttl_seconds <= 0:
            return

        payload = _serialize(challenge)
        encrypted = self._fernet.encrypt(payload)
        await self._redis.set(
            self._key(challenge.identity.session_id),
            encrypted,
            ex=ttl_seconds,
        )

    async def get(self, session_id: SessionIdentity) -> PendingChallenge | None:
        """GET → decrypt → deserialize → PendingChallenge or None."""
        data = await self._redis.get(self._key(session_id.session_id))
        if data is None:
            return None
        try:
            decrypted = self._fernet.decrypt(data)
        except InvalidToken:
            return None
        return _deserialize(decrypted)

    async def delete(self, session_id: SessionIdentity) -> None:
        """DEL key."""
        await self._redis.delete(self._key(session_id.session_id))
