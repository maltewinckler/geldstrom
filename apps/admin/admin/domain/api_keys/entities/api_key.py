"""API Key entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash


class ApiKey(BaseModel, frozen=True):
    """API Key entity representing a single API key credential.

    Carries a KeyHash, a KeyStatus, and a reference to its owning Account.
    """

    id: UUID
    account_id: UUID
    key_hash: KeyHash  # Argon2id hash — persisted to PostgreSQL
    sha256_key_hash: SHA256KeyHash  # SHA-256 digest — for gRPC lookup
    status: KeyStatus
    created_at: datetime
    revoked_at: datetime | None = None
