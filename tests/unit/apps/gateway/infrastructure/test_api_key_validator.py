"""Unit tests for GrpcApiKeyValidator.

Tests gRPC validation flow, error handling, and SHA-256 hashing.
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from gateway.domain.session.value_objects.audit import ApiKeyValidationResult
from gateway.infrastructure.session.api_key_validator import (
    ApiKeyValidationError,
    GrpcApiKeyValidator,
    _hash_api_key,
)


@pytest.fixture
def mock_channel() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_stub() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def validator(mock_channel: MagicMock, mock_stub: AsyncMock) -> GrpcApiKeyValidator:
    with patch(
        "gateway.infrastructure.session.api_key_validator.KeyValidationServiceStub",
        return_value=mock_stub,
    ):
        return GrpcApiKeyValidator(channel=mock_channel)


def _make_grpc_response(
    is_valid: bool = True,
    account_id: str = "acct-123",
) -> MagicMock:
    """Create a mock gRPC response object."""
    resp = MagicMock()
    resp.is_valid = is_valid
    resp.account_id = account_id
    return resp


# --- Helper function tests ---


def test_hash_api_key_uses_sha256() -> None:
    """_hash_api_key should return the SHA-256 hex digest of the input."""
    key = "my-secret-api-key"
    expected = hashlib.sha256(key.encode()).hexdigest()
    assert _hash_api_key(key) == expected


def test_hash_api_key_deterministic() -> None:
    """Same input should always produce the same hash."""
    assert _hash_api_key("key-abc") == _hash_api_key("key-abc")


def test_hash_api_key_different_inputs() -> None:
    """Different inputs should produce different hashes."""
    assert _hash_api_key("key-a") != _hash_api_key("key-b")


# --- gRPC validation tests ---


@pytest.mark.asyncio
async def test_validate_calls_grpc(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should call gRPC ValidateKey."""
    mock_stub.ValidateKey = AsyncMock(
        return_value=_make_grpc_response(is_valid=True, account_id="acct-grpc")
    )

    result = await validator.validate("test-key")

    assert result.is_valid is True
    assert result.account_id == "acct-grpc"
    mock_stub.ValidateKey.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_passes_key_hash(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should pass the SHA-256 hash (not the raw key) to gRPC."""
    mock_stub.ValidateKey = AsyncMock(return_value=_make_grpc_response())

    await validator.validate("secret-key")

    call_args = mock_stub.ValidateKey.call_args
    request = call_args.args[0]
    assert request.key_hash == _hash_api_key("secret-key")


@pytest.mark.asyncio
async def test_validate_invalid_key_from_grpc(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should return invalid result when gRPC says key is invalid."""
    mock_stub.ValidateKey = AsyncMock(
        return_value=_make_grpc_response(is_valid=False, account_id="")
    )

    result = await validator.validate("bad-key")

    assert result.is_valid is False
    assert result.account_id is None


@pytest.mark.asyncio
async def test_validate_empty_account_id_becomes_none(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should convert empty account_id to None."""
    mock_stub.ValidateKey = AsyncMock(
        return_value=_make_grpc_response(is_valid=True, account_id="")
    )

    result = await validator.validate("key")

    assert result.account_id is None


# --- gRPC error tests ---


@pytest.mark.asyncio
async def test_validate_raises_on_grpc_rpc_error(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should raise ApiKeyValidationError when gRPC call fails with RpcError."""
    mock_stub.ValidateKey = AsyncMock(side_effect=grpc.RpcError())

    with pytest.raises(ApiKeyValidationError):
        await validator.validate("any-key")


@pytest.mark.asyncio
async def test_validate_raises_on_generic_error(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should raise ApiKeyValidationError when gRPC call fails with any exception."""
    mock_stub.ValidateKey = AsyncMock(side_effect=ConnectionError("connection refused"))

    with pytest.raises(ApiKeyValidationError) as exc_info:
        await validator.validate("any-key")

    assert "connection refused" in str(exc_info.value)


# --- Result structure tests ---


@pytest.mark.asyncio
async def test_validate_returns_correct_result_type(
    validator: GrpcApiKeyValidator,
    mock_stub: AsyncMock,
) -> None:
    """validate() should return an ApiKeyValidationResult."""
    mock_stub.ValidateKey = AsyncMock(
        return_value=_make_grpc_response(is_valid=True, account_id="acct-1")
    )

    result = await validator.validate("key")

    assert isinstance(result, ApiKeyValidationResult)
    assert result.is_valid is True
    assert result.account_id == "acct-1"
    assert result.metadata is None
