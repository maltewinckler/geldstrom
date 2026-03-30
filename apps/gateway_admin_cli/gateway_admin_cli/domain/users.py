"""User domain model and value objects for the admin CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from .errors import DomainError, ValidationError

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserStatus(StrEnum):
    """Lifecycle status for an API consumer / user."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


@dataclass(frozen=True)
class UserId:
    """Strongly typed entity identifier for users."""

    value: UUID

    @classmethod
    def from_string(cls, raw: str) -> UserId:
        return cls(UUID(raw))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Email:
    """Normalized, validated email address."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().casefold()
        if not _EMAIL_PATTERN.match(normalized):
            raise DomainError("Email must contain a valid email address")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ApiKeyHash:
    """Stored password-grade hash of an API key."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("ApiKeyHash must not be empty")

    def __str__(self) -> str:
        return self.value


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
