"""Bank directory repository using Admin gRPC GetBankEndpoint.

Implements the BankDirectoryRepository port by calling Admin gRPC
GetBankEndpoint on each request. No local caching — Admin service
maintains its own internal cache.

This is the "dumb Gateway" pattern: Gateway delegates all configuration
lookups to Admin via gRPC, keeping Gateway focused purely on banking
protocol execution.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import grpc
from pydantic import SecretStr

from gateway.domain.banking.value_objects.connection import (
    BankEndpoint,
    BankingProtocol,
)
from gateway.infrastructure.grpc.generated import bank_directory_pb2
from gateway.infrastructure.grpc.generated.bank_directory_pb2_grpc import (
    BankDirectoryServiceStub,
)

if TYPE_CHECKING:
    from grpc.aio import Channel

logger = logging.getLogger(__name__)


class BankEndpointNotFoundError(Exception):
    """Raised when a bank endpoint is not found in the Admin service."""

    def __init__(self, bank_code: str) -> None:
        self.bank_code = bank_code
        super().__init__(f"Bank endpoint not found: {bank_code}")


class BankDirectoryUnavailableError(Exception):
    """Raised when the Admin gRPC service is unavailable."""

    def __init__(self, reason: str | None = None) -> None:
        self.reason = reason
        msg = "Bank directory service unavailable"
        if reason:
            msg = f"{msg}: {reason}"
        super().__init__(msg)


class GrpcBankDirectoryRepository:
    """Implements BankDirectoryRepository port using Admin gRPC GetBankEndpoint.

    Calls Admin gRPC on every request — no local caching.
    Admin maintains its own internal cache for fast lookups.
    """

    def __init__(self, channel: Channel) -> None:
        self._stub = BankDirectoryServiceStub(channel)

    async def resolve(
        self, bank_code: str, protocol: BankingProtocol
    ) -> BankEndpoint | None:
        """Resolve a bank endpoint via Admin gRPC GetBankEndpoint.

        Returns None if the endpoint is not found.
        Raises BankDirectoryUnavailableError if Admin is unavailable.
        """
        try:
            request = bank_directory_pb2.GetBankEndpointRequest(bank_code=bank_code)
            response = await self._stub.GetBankEndpoint(request)
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.NOT_FOUND:
                logger.debug("Bank endpoint not found: %s", bank_code)
                return None
            logger.error("gRPC error resolving bank endpoint: %s", exc)
            raise BankDirectoryUnavailableError(reason=str(exc)) from exc
        except Exception as exc:
            logger.error("Error resolving bank endpoint: %s", exc)
            raise BankDirectoryUnavailableError(reason=str(exc)) from exc

        # Verify protocol matches (Admin returns the protocol from the endpoint)
        try:
            response_protocol = BankingProtocol(response.protocol)
        except ValueError:
            logger.warning(
                "Unknown protocol for bank %s: %s",
                bank_code,
                response.protocol,
            )
            return None

        if response_protocol != protocol:
            logger.warning(
                "Protocol mismatch for bank %s: requested %s, got %s",
                bank_code,
                protocol,
                response_protocol,
            )
            return None

        # Build BankEndpoint with FinTS-specific fields from gRPC response
        fints_product_id: SecretStr | None = None
        fints_product_version: str | None = None
        fints_country_code: str | None = None

        if response_protocol == BankingProtocol.FINTS:
            if response.fints_product_id:
                fints_product_id = SecretStr(response.fints_product_id)
            if response.fints_product_version:
                fints_product_version = response.fints_product_version
            if response.fints_country_code:
                fints_country_code = response.fints_country_code

        return BankEndpoint(
            server_url=response.server_url,
            protocol=response_protocol,
            metadata=dict(response.metadata) if response.metadata else None,
            fints_product_id=fints_product_id,
            fints_product_version=fints_product_version,
            fints_country_code=fints_country_code,
        )
