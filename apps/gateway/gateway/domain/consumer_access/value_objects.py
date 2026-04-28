"""Value objects for the consumer access domain."""

from __future__ import annotations

from enum import StrEnum

from pydantic import RootModel, field_validator

from gateway.domain import DomainError


class ConsumerStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class ApiKeyHash(RootModel[str], frozen=True):
    """Stored password-grade hash of an API key."""

    @field_validator("root")
    @classmethod
    def _must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise DomainError("ApiKeyHash must not be empty")
        return v

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root
