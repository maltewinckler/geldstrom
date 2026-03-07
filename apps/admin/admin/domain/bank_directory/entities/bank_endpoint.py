"""Bank endpoint entity."""

from pydantic import BaseModel

from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import ProtocolConfig


class BankEndpoint(BaseModel, frozen=True):
    """Bank endpoint entity representing a bank's connection parameters."""

    bank_code: str  # Primary key, max 20 chars
    protocol: BankingProtocol
    server_url: str  # Validated HTTP/HTTPS URL
    protocol_config: ProtocolConfig  # Protocol-specific settings (decrypted in memory)
    metadata: dict | None = None
