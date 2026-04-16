"""User aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from gateway_admin.domain.errors import DomainError, ValidationError
from gateway_admin.domain.value_objects.user import ApiKeyHash, Email, UserId


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


@dataclass
class User:
    """Aggregate root representing one API consumer."""

    user_id: UserId
    email: Email
    api_key_hash: ApiKeyHash | None
    status: UserStatus
    created_at: datetime
    rotated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status is UserStatus.ACTIVE and self.api_key_hash is None:
            raise DomainError("Active User instances must have an ApiKeyHash")

    def disable(self) -> None:
        self.status = UserStatus.DISABLED

    def mark_deleted(self) -> None:
        self.status = UserStatus.DELETED

    def reactivate(self, api_key_hash: ApiKeyHash) -> None:
        if self.status is UserStatus.DELETED:
            raise ValidationError("Deleted users cannot be reactivated")
        self.api_key_hash = api_key_hash
        self.status = UserStatus.ACTIVE
