"""API schemas for the api_keys bounded context."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from admin.domain.api_keys.value_objects.key_status import KeyStatus


class CreateAccountRequest(BaseModel):
    """Request body for creating an account."""

    account_id: UUID


class ApiKeySummary(BaseModel):
    """Summary of an API key (no key material)."""

    key_id: UUID
    status: KeyStatus
    created_at: datetime


class AccountResponse(BaseModel):
    """Response body for account retrieval."""

    account_id: UUID
    created_at: datetime
    api_keys: list[ApiKeySummary]


class CreateApiKeyRequest(BaseModel):
    """Request body for creating an API key."""

    account_id: UUID


class CreateApiKeyResponse(BaseModel):
    """Response body for API key creation.

    Contains the raw key which is returned exactly once.
    """

    key_id: UUID
    raw_key: str  # Returned exactly once
