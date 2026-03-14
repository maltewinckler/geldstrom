"""Aggregate for API consumer access control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gateway.domain.shared import DomainError

from .value_objects import ApiKeyHash, ConsumerId, ConsumerStatus, EmailAddress


@dataclass
class ApiConsumer:
    """Aggregate root representing one API consumer."""

    consumer_id: ConsumerId
    email: EmailAddress
    api_key_hash: ApiKeyHash | None
    status: ConsumerStatus
    created_at: datetime
    rotated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status is ConsumerStatus.ACTIVE and self.api_key_hash is None:
            raise DomainError("Active ApiConsumer instances must have an ApiKeyHash")

    def disable(self) -> None:
        self.status = ConsumerStatus.DISABLED

    def mark_deleted(self) -> None:
        self.status = ConsumerStatus.DELETED

    def reactivate(self, api_key_hash: ApiKeyHash) -> None:
        if self.status is ConsumerStatus.DELETED:
            raise DomainError("Deleted ApiConsumer instances cannot be reactivated")
        self.api_key_hash = api_key_hash
        self.status = ConsumerStatus.ACTIVE
