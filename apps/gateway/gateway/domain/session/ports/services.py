"""Session-level service ports — API key validation and audit publishing."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gateway.domain.session.value_objects.audit import (
    ApiKeyValidationResult,
    AuditEvent,
)


@runtime_checkable
class ApiKeyValidator(Protocol):
    """Validates API keys and returns account identity."""

    async def validate(self, api_key: str) -> ApiKeyValidationResult: ...


@runtime_checkable
class AuditEventPublisher(Protocol):
    """Publishes audit events to an audit sink."""

    async def publish(self, event: AuditEvent) -> None: ...
