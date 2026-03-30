"""Aggregate for API consumer access control."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from gateway.domain import DomainError

from .value_objects import ApiKeyHash, ConsumerStatus


class ApiConsumer(BaseModel):
    """Aggregate root representing one API consumer."""

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

    @model_validator(mode="after")
    def _check_active_has_hash(self) -> ApiConsumer:
        if self.status is ConsumerStatus.ACTIVE and self.api_key_hash is None:
            raise ValueError("Active ApiConsumer instances must have an ApiKeyHash")
        return self

    def disable(self) -> None:
        self.status = ConsumerStatus.DISABLED

    def mark_deleted(self) -> None:
        self.status = ConsumerStatus.DELETED

    def reactivate(self, api_key_hash: ApiKeyHash) -> None:
        if self.status is ConsumerStatus.DELETED:
            raise DomainError("Deleted ApiConsumer instances cannot be reactivated")
        self.api_key_hash = api_key_hash
        self.status = ConsumerStatus.ACTIVE
