"""Operational value objects — audit and API key validation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from gateway.domain.banking.value_objects.connection import BankingProtocol


# Value Object — operational audit record
class AuditEvent(BaseModel, frozen=True):
    """Immutable record of an API request for audit purposes.

    Value Object: created once, never mutated, published to audit sink.
    """

    timestamp: datetime
    account_id: str
    remote_ip: str
    request_type: str
    protocol: BankingProtocol | None = None


# Value Object — result of API key validation
class ApiKeyValidationResult(BaseModel, frozen=True):
    """Result of validating an API key against the admin service.

    Value Object: immutable, produced by ApiKeyValidator port.
    """

    is_valid: bool
    account_id: str | None = None
    metadata: dict | None = None
