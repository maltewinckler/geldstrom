"""Unit tests for RedisChallengeRepository.

Tests save/get/delete operations with mocked Redis, verifying encryption
round-trip, TTL calculation, key pattern, and edge cases.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.session.entities.pending_challenge import PendingChallenge
from gateway.domain.session.value_objects.session_identity import SessionIdentity
from gateway.infrastructure.session.challenge_repo import (
    RedisChallengeRepository,
    _deserialize,
    _serialize,
)


@pytest.fixture
def encryption_key() -> bytes:
    return Fernet.generate_key()


@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repo(mock_redis: AsyncMock, encryption_key: bytes) -> RedisChallengeRepository:
    return RedisChallengeRepository(redis=mock_redis, encryption_key=encryption_key)


def _make_challenge(
    session_id: str = "abc123",
    expires_in_seconds: int = 300,
) -> PendingChallenge:
    return PendingChallenge(
        identity=SessionIdentity(
            session_id=session_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
        ),
        protocol=BankingProtocol.FINTS,
        bank_code="12345678",
        dialog_state=b"opaque-state-bytes",
        challenge_type="photoTAN",
        challenge_text="Enter the code",
        media_data=b"\x89PNG\r\n",
    )


@pytest.mark.asyncio
async def test_save_encrypts_and_sets_with_ttl(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
    encryption_key: bytes,
) -> None:
    """save() should encrypt the challenge JSON and SET it in Redis with a TTL."""
    challenge = _make_challenge(session_id="sess1", expires_in_seconds=200)

    await repo.save(challenge)

    mock_redis.set.assert_awaited_once()
    call_args = mock_redis.set.call_args
    key = call_args.args[0]
    encrypted_blob = call_args.args[1]

    assert key == "gateway:challenge:sess1"
    # TTL should be close to 200 (allow 5s tolerance for test execution time)
    ttl = call_args.kwargs["ex"]
    assert 195 <= ttl <= 200

    # Verify the blob is actually encrypted and decryptable
    fernet = Fernet(encryption_key)
    decrypted = fernet.decrypt(encrypted_blob)

    roundtripped = _deserialize(decrypted)
    assert roundtripped.identity.session_id == "sess1"
    assert roundtripped.dialog_state == b"opaque-state-bytes"
    assert roundtripped.challenge_type == "photoTAN"
    assert roundtripped.media_data == b"\x89PNG\r\n"


@pytest.mark.asyncio
async def test_save_skips_expired_session(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
) -> None:
    """save() should not store anything if the session has already expired."""
    challenge = _make_challenge(expires_in_seconds=-10)

    await repo.save(challenge)

    mock_redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_decrypts_and_returns_challenge(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
    encryption_key: bytes,
) -> None:
    """get() should decrypt the stored blob and return a PendingChallenge."""
    challenge = _make_challenge(session_id="sess2")
    fernet = Fernet(encryption_key)
    encrypted = fernet.encrypt(_serialize(challenge))
    mock_redis.get = AsyncMock(return_value=encrypted)

    identity = SessionIdentity(
        session_id="sess2",
        expires_at=datetime.now(UTC) + timedelta(seconds=300),
    )
    result = await repo.get(identity)

    mock_redis.get.assert_awaited_once_with("gateway:challenge:sess2")
    assert result is not None
    assert result.identity.session_id == "sess2"
    assert result.dialog_state == challenge.dialog_state
    assert result.challenge_text == "Enter the code"
    assert result.media_data == b"\x89PNG\r\n"


@pytest.mark.asyncio
async def test_get_returns_none_when_key_missing(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
) -> None:
    """get() should return None when the key doesn't exist in Redis."""
    mock_redis.get = AsyncMock(return_value=None)

    identity = SessionIdentity(
        session_id="nonexistent",
        expires_at=datetime.now(UTC) + timedelta(seconds=300),
    )
    result = await repo.get(identity)

    assert result is None


@pytest.mark.asyncio
async def test_get_returns_none_on_invalid_token(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
) -> None:
    """get() should return None if decryption fails (corrupted/wrong key)."""
    mock_redis.get = AsyncMock(return_value=b"corrupted-data")

    identity = SessionIdentity(
        session_id="bad",
        expires_at=datetime.now(UTC) + timedelta(seconds=300),
    )
    result = await repo.get(identity)

    assert result is None


@pytest.mark.asyncio
async def test_delete_removes_key(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
) -> None:
    """delete() should DEL the key from Redis."""
    identity = SessionIdentity(
        session_id="sess3",
        expires_at=datetime.now(UTC) + timedelta(seconds=300),
    )

    await repo.delete(identity)

    mock_redis.delete.assert_awaited_once_with("gateway:challenge:sess3")


@pytest.mark.asyncio
async def test_save_get_roundtrip_with_none_optional_fields(
    repo: RedisChallengeRepository,
    mock_redis: AsyncMock,
    encryption_key: bytes,
) -> None:
    """Round-trip works when optional fields are None."""
    challenge = PendingChallenge(
        identity=SessionIdentity(
            session_id="minimal",
            expires_at=datetime.now(UTC) + timedelta(seconds=300),
        ),
        protocol=BankingProtocol.FINTS,
        bank_code="12345678",
        dialog_state=b"state",
        challenge_type="smsTAN",
        challenge_text=None,
        media_data=None,
    )

    # Capture what save() would store
    fernet = Fernet(encryption_key)
    encrypted = fernet.encrypt(_serialize(challenge))
    mock_redis.get = AsyncMock(return_value=encrypted)

    identity = challenge.identity
    result = await repo.get(identity)

    assert result is not None
    assert result.challenge_text is None
    assert result.media_data is None
    assert result.challenge_type == "smsTAN"
