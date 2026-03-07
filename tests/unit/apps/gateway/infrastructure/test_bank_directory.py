"""Unit tests for GrpcBankDirectoryRepository.

Tests gRPC GetBankEndpoint calls, error handling, and BankEndpoint construction.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from gateway.domain.banking.value_objects.connection import (
    BankEndpoint,
    BankingProtocol,
)
from gateway.infrastructure.banking.directory import (
    BankDirectoryUnavailableError,
    GrpcBankDirectoryRepository,
)


@pytest.fixture
def mock_channel() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_stub() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repo(mock_channel: MagicMock, mock_stub: AsyncMock) -> GrpcBankDirectoryRepository:
    with patch(
        "gateway.infrastructure.banking.directory.BankDirectoryServiceStub",
        return_value=mock_stub,
    ):
        return GrpcBankDirectoryRepository(channel=mock_channel)


def _make_grpc_response(
    bank_code: str = "12345678",
    protocol: str = "fints",
    server_url: str = "https://fints.example.com/fints",
    fints_product_id: str = "product-123",
    fints_product_version: str = "1.0.0",
    fints_country_code: str = "DE",
    metadata: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock gRPC BankEndpointResponse."""
    resp = MagicMock()
    resp.bank_code = bank_code
    resp.protocol = protocol
    resp.server_url = server_url
    resp.fints_product_id = fints_product_id
    resp.fints_product_version = fints_product_version
    resp.fints_country_code = fints_country_code
    resp.metadata = metadata or {}
    return resp


# --- resolve() success tests ---


@pytest.mark.asyncio
async def test_resolve_calls_grpc(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should call GetBankEndpoint on the gRPC stub."""
    mock_stub.GetBankEndpoint = AsyncMock(return_value=_make_grpc_response())

    await repo.resolve("12345678", BankingProtocol.FINTS)

    mock_stub.GetBankEndpoint.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_passes_bank_code(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should pass the bank_code to gRPC."""
    mock_stub.GetBankEndpoint = AsyncMock(return_value=_make_grpc_response())

    await repo.resolve("87654321", BankingProtocol.FINTS)

    call_args = mock_stub.GetBankEndpoint.call_args
    request = call_args.args[0]
    assert request.bank_code == "87654321"


@pytest.mark.asyncio
async def test_resolve_returns_bank_endpoint(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should return a BankEndpoint with correct fields."""
    mock_stub.GetBankEndpoint = AsyncMock(
        return_value=_make_grpc_response(
            bank_code="12070000",
            protocol="fints",
            server_url="https://banking.example.de/fints",
            fints_product_id="my-product",
            fints_product_version="2.0.0",
            fints_country_code="DE",
            metadata={"region": "EU"},
        )
    )

    result = await repo.resolve("12070000", BankingProtocol.FINTS)

    assert result is not None
    assert isinstance(result, BankEndpoint)
    assert result.server_url == "https://banking.example.de/fints"
    assert result.protocol == BankingProtocol.FINTS
    assert result.fints_product_id is not None
    assert result.fints_product_id.get_secret_value() == "my-product"
    assert result.fints_product_version == "2.0.0"
    assert result.fints_country_code == "DE"
    assert result.metadata == {"region": "EU"}


@pytest.mark.asyncio
async def test_resolve_handles_empty_fints_fields(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should set FinTS fields to None when empty in response."""
    mock_stub.GetBankEndpoint = AsyncMock(
        return_value=_make_grpc_response(
            fints_product_id="",
            fints_product_version="",
            fints_country_code="",
        )
    )

    result = await repo.resolve("12345678", BankingProtocol.FINTS)

    assert result is not None
    assert result.fints_product_id is None
    assert result.fints_product_version is None
    assert result.fints_country_code is None


@pytest.mark.asyncio
async def test_resolve_handles_empty_metadata(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should set metadata to None when empty in response."""
    mock_stub.GetBankEndpoint = AsyncMock(return_value=_make_grpc_response(metadata={}))

    result = await repo.resolve("12345678", BankingProtocol.FINTS)

    assert result is not None
    assert result.metadata is None


# --- resolve() NOT_FOUND tests ---


@pytest.mark.asyncio
async def test_resolve_returns_none_on_not_found(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should return None when gRPC returns NOT_FOUND."""
    error = grpc.RpcError()
    error.code = MagicMock(return_value=grpc.StatusCode.NOT_FOUND)
    mock_stub.GetBankEndpoint = AsyncMock(side_effect=error)

    result = await repo.resolve("nonexistent", BankingProtocol.FINTS)

    assert result is None


# --- resolve() protocol mismatch tests ---


@pytest.mark.asyncio
async def test_resolve_returns_none_on_protocol_mismatch(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should return None when response protocol doesn't match request."""
    # Response has protocol "ebics" but we requested "fints"
    mock_stub.GetBankEndpoint = AsyncMock(
        return_value=_make_grpc_response(protocol="ebics")
    )

    result = await repo.resolve("12345678", BankingProtocol.FINTS)

    assert result is None


# --- resolve() error tests ---


@pytest.mark.asyncio
async def test_resolve_raises_on_grpc_unavailable(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should raise BankDirectoryUnavailableError on UNAVAILABLE."""
    error = grpc.RpcError()
    error.code = MagicMock(return_value=grpc.StatusCode.UNAVAILABLE)
    mock_stub.GetBankEndpoint = AsyncMock(side_effect=error)

    with pytest.raises(BankDirectoryUnavailableError):
        await repo.resolve("12345678", BankingProtocol.FINTS)


@pytest.mark.asyncio
async def test_resolve_raises_on_generic_grpc_error(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should raise BankDirectoryUnavailableError on other gRPC errors."""
    error = grpc.RpcError()
    error.code = MagicMock(return_value=grpc.StatusCode.INTERNAL)
    mock_stub.GetBankEndpoint = AsyncMock(side_effect=error)

    with pytest.raises(BankDirectoryUnavailableError):
        await repo.resolve("12345678", BankingProtocol.FINTS)


@pytest.mark.asyncio
async def test_resolve_raises_on_connection_error(
    repo: GrpcBankDirectoryRepository,
    mock_stub: AsyncMock,
) -> None:
    """resolve() should raise BankDirectoryUnavailableError on connection errors."""
    mock_stub.GetBankEndpoint = AsyncMock(
        side_effect=ConnectionError("connection refused")
    )

    with pytest.raises(BankDirectoryUnavailableError) as exc_info:
        await repo.resolve("12345678", BankingProtocol.FINTS)

    assert "connection refused" in str(exc_info.value)
