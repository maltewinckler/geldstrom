"""Use cases for the bank_directory bounded context."""

from pydantic import SecretStr

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.ports.repository import BankEndpointRepository
from admin.domain.bank_directory.ports.services import EndpointCache
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.domain.exceptions import (
    BankEndpointAlreadyExistsError,
    BankEndpointNotFoundError,
)

# Redacted protocol config for REST API responses (no secrets)
REDACTED_PROTOCOL_CONFIG = FinTSConfig(
    product_id=SecretStr("***REDACTED***"),
    product_version="***REDACTED***",
    country_code="***REDACTED***",
)


def _redact_endpoint(endpoint: BankEndpoint) -> BankEndpoint:
    """Return a copy of the endpoint with redacted protocol_config."""
    return BankEndpoint(
        bank_code=endpoint.bank_code,
        protocol=endpoint.protocol,
        server_url=endpoint.server_url,
        protocol_config=REDACTED_PROTOCOL_CONFIG,
        metadata=endpoint.metadata,
    )


class CreateBankEndpoint:
    """Use case for creating a new bank endpoint."""

    def __init__(
        self,
        bank_endpoint_repo: BankEndpointRepository,
        endpoint_cache: EndpointCache,
    ) -> None:
        self._bank_endpoint_repo = bank_endpoint_repo
        self._endpoint_cache = endpoint_cache

    async def execute(self, endpoint: BankEndpoint) -> None:
        """Create a new bank endpoint.

        Raises:
            BankEndpointAlreadyExistsError: If a bank endpoint with the same
                bank_code already exists.
        """
        # 1. Check endpoint doesn't exist
        existing = await self._bank_endpoint_repo.get(endpoint.bank_code)
        if existing is not None:
            raise BankEndpointAlreadyExistsError(
                f"Bank endpoint {endpoint.bank_code} already exists"
            )

        # 2. Persist to PostgreSQL (encryption handled by repository)
        await self._bank_endpoint_repo.save(endpoint)

        # 3. Update internal cache (with decrypted config)
        await self._endpoint_cache.set(endpoint)


class UpdateBankEndpoint:
    """Use case for updating an existing bank endpoint."""

    def __init__(
        self,
        bank_endpoint_repo: BankEndpointRepository,
        endpoint_cache: EndpointCache,
    ) -> None:
        self._bank_endpoint_repo = bank_endpoint_repo
        self._endpoint_cache = endpoint_cache

    async def execute(self, endpoint: BankEndpoint) -> None:
        """Update an existing bank endpoint.

        Raises:
            BankEndpointNotFoundError: If the bank endpoint does not exist.
        """
        # 1. Check endpoint exists
        existing = await self._bank_endpoint_repo.get(endpoint.bank_code)
        if existing is None:
            raise BankEndpointNotFoundError(
                f"Bank endpoint {endpoint.bank_code} not found"
            )

        # 2. Update in PostgreSQL (re-encrypting the config)
        await self._bank_endpoint_repo.update(endpoint)

        # 3. Refresh the cache (with decrypted config)
        await self._endpoint_cache.set(endpoint)


class DeleteBankEndpoint:
    """Use case for deleting a bank endpoint."""

    def __init__(
        self,
        bank_endpoint_repo: BankEndpointRepository,
        endpoint_cache: EndpointCache,
    ) -> None:
        self._bank_endpoint_repo = bank_endpoint_repo
        self._endpoint_cache = endpoint_cache

    async def execute(self, bank_code: str) -> None:
        """Delete a bank endpoint.

        Raises:
            BankEndpointNotFoundError: If the bank endpoint does not exist.
        """
        # 1. Check endpoint exists
        existing = await self._bank_endpoint_repo.get(bank_code)
        if existing is None:
            raise BankEndpointNotFoundError(f"Bank endpoint {bank_code} not found")

        # 2. Delete from PostgreSQL
        await self._bank_endpoint_repo.delete(bank_code)

        # 3. Remove from cache
        await self._endpoint_cache.delete(bank_code)


class GetBankEndpoint:
    """Use case for retrieving a bank endpoint."""

    def __init__(
        self,
        bank_endpoint_repo: BankEndpointRepository,
    ) -> None:
        self._bank_endpoint_repo = bank_endpoint_repo

    async def execute(self, bank_code: str) -> BankEndpoint:
        """Retrieve a bank endpoint with redacted protocol_config.

        Raises:
            BankEndpointNotFoundError: If the bank endpoint does not exist.
        """
        endpoint = await self._bank_endpoint_repo.get(bank_code)
        if endpoint is None:
            raise BankEndpointNotFoundError(f"Bank endpoint {bank_code} not found")

        # Return with redacted protocol_config (no secrets in REST response)
        return _redact_endpoint(endpoint)


class ListBankEndpoints:
    """Use case for listing all bank endpoints."""

    def __init__(
        self,
        bank_endpoint_repo: BankEndpointRepository,
    ) -> None:
        self._bank_endpoint_repo = bank_endpoint_repo

    async def execute(self) -> list[BankEndpoint]:
        """List all bank endpoints with redacted protocol_config."""
        endpoints = await self._bank_endpoint_repo.list_all()

        # Return with redacted protocol_config (no secrets in REST response)
        return [_redact_endpoint(endpoint) for endpoint in endpoints]
