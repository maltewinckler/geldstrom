"""Bank directory service ports."""

from typing import Protocol

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import ProtocolConfig


class EndpointCache(Protocol):
    """Internal cache for fast endpoint lookup. Implementation detail."""

    async def get(self, bank_code: str) -> BankEndpoint | None:
        """Get a cached bank endpoint by bank code."""
        ...

    async def set(self, endpoint: BankEndpoint) -> None:
        """Cache a bank endpoint."""
        ...

    async def delete(self, bank_code: str) -> None:
        """Remove a bank endpoint from cache."""
        ...

    async def load_all(self, endpoints: list[BankEndpoint]) -> None:
        """Load all endpoints into cache."""
        ...


class ConfigEncryptor(Protocol):
    """Encrypts/decrypts protocol_config for storage."""

    def encrypt(self, config: ProtocolConfig) -> bytes:
        """Encrypt a protocol config for storage."""
        ...

    def decrypt(self, data: bytes, protocol: BankingProtocol) -> ProtocolConfig:
        """Decrypt stored protocol config data."""
        ...
