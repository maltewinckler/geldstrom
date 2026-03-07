"""Bank endpoint repository port."""

from typing import Protocol

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint


class BankEndpointRepository(Protocol):
    """Repository interface for bank endpoint persistence."""

    async def get(self, bank_code: str) -> BankEndpoint | None:
        """Get a bank endpoint by bank code."""
        ...

    async def list_all(self) -> list[BankEndpoint]:
        """List all bank endpoints."""
        ...

    async def save(self, endpoint: BankEndpoint) -> None:
        """Save a new bank endpoint."""
        ...

    async def update(self, endpoint: BankEndpoint) -> None:
        """Update an existing bank endpoint."""
        ...

    async def delete(self, bank_code: str) -> None:
        """Delete a bank endpoint by bank code."""
        ...
