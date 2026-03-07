"""Banking connection value objects.

Value Objects: immutable, identity by value, no lifecycle.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, SecretStr


class BankingProtocol(StrEnum):
    """Supported banking wire protocols."""

    FINTS = "fints"


# Value Object — identity by (protocol, bank_code, username, pin)
class BankConnection(BaseModel, frozen=True):
    """Credentials and protocol for a single bank connection attempt.

    Value Object: immutable, equality by field values.
    Credentials are SecretStr to prevent accidental log/repr leakage.
    """

    protocol: BankingProtocol
    bank_code: str
    username: SecretStr
    pin: SecretStr


# Value Object — identity by (server_url, protocol)
class BankEndpoint(BaseModel, frozen=True):
    """Resolved network endpoint for a bank.

    Value Object: immutable, looked up from BankDirectoryRepository.
    Protocol-specific fields (fints_*) are populated from the Admin gRPC
    GetBankEndpoint response and allow per-bank product credentials.
    """

    server_url: str
    protocol: BankingProtocol
    metadata: dict | None = None
    # FinTS-specific fields (populated from Admin gRPC response)
    fints_product_id: SecretStr | None = None
    fints_product_version: str | None = None
    fints_country_code: str | None = None
