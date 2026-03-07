"""In-memory endpoint cache implementation."""

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint


class InMemoryEndpointCache:
    """Simple dict-based cache for bank endpoints.

    Stores decrypted BankEndpoint entities for fast gRPC lookups.
    """

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._cache: dict[str, BankEndpoint] = {}  # bank_code -> BankEndpoint

    async def get(self, bank_code: str) -> BankEndpoint | None:
        """Get a cached bank endpoint by bank code."""
        return self._cache.get(bank_code)

    async def set(self, endpoint: BankEndpoint) -> None:
        """Cache a bank endpoint."""
        self._cache[endpoint.bank_code] = endpoint

    async def delete(self, bank_code: str) -> None:
        """Remove a bank endpoint from cache."""
        self._cache.pop(bank_code, None)

    async def load_all(self, endpoints: list[BankEndpoint]) -> None:
        """Load all endpoints into cache."""
        for endpoint in endpoints:
            self._cache[endpoint.bank_code] = endpoint
