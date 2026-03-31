"""Read-only aggregate for API consumer access control."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from .value_objects import ApiKeyHash, ConsumerStatus


class ApiConsumer(BaseModel):
    """Read-only projection of an API consumer used for gateway authentication."""

    model_config = {"frozen": True}

    consumer_id: UUID
    email: EmailStr
    api_key_hash: ApiKeyHash | None
    status: ConsumerStatus
    created_at: datetime
    rotated_at: datetime | None = None

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    def is_disabled(self) -> bool:
        """Return True when this consumer's access has been revoked."""
        return self.status is ConsumerStatus.DISABLED

    @model_validator(mode="after")
    def _check_active_has_hash(self) -> ApiConsumer:
        if self.status is ConsumerStatus.ACTIVE and self.api_key_hash is None:
            raise ValueError("Active ApiConsumer instances must have an ApiKeyHash")
        return self
