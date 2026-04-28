"""Authenticate gateway consumers via direct database lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.domain.audit import AuditEventType
from gateway.domain.consumer_access import (
    ApiConsumerRepository,
    ApiKeyVerifier,
)

if TYPE_CHECKING:
    from gateway.application.audit import AuditService
    from gateway.application.ports import ApplicationFactory


class AuthenticateConsumerQuery:
    """Authenticate a presented API key against stored consumer hashes."""

    def __init__(
        self,
        consumer_repository: ApiConsumerRepository,
        api_key_verifier: ApiKeyVerifier,
        audit_service: AuditService,
    ) -> None:
        self._consumer_repository = consumer_repository
        self._api_key_verifier = api_key_verifier
        self._audit_service = audit_service

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            factory.repos.consumer,
            factory.api_key_verifier,
            factory.audit_service,
        )

    async def __call__(self, presented_key: str) -> UUID:
        prefix, _, secret = presented_key.partition(".")
        if not secret:
            await self._audit_service.record(AuditEventType.CONSUMER_AUTH_FAILED, None)
            raise UnauthorizedError("Invalid API key")

        consumer = await self._consumer_repository.get_by_key_prefix(prefix)
        if consumer is None:
            await self._audit_service.record(AuditEventType.CONSUMER_AUTH_FAILED, None)
            raise UnauthorizedError("Invalid API key")

        if consumer.is_disabled():
            await self._audit_service.record(
                AuditEventType.CONSUMER_AUTH_FAILED, consumer.consumer_id
            )
            raise ForbiddenError("API consumer is disabled")

        # consumer.api_key_hash is non-None here: the ACTIVE invariant on
        # ApiConsumer guarantees it (enforced by _check_active_has_hash).
        # The query only returns ACTIVE and DISABLED, so not-disabled implies active.
        if not self._api_key_verifier.verify(presented_key, consumer.api_key_hash):  # type: ignore[arg-type]
            await self._audit_service.record(AuditEventType.CONSUMER_AUTH_FAILED, None)
            raise UnauthorizedError("Invalid API key")

        await self._audit_service.record(
            AuditEventType.CONSUMER_AUTHENTICATED, consumer.consumer_id
        )
        return consumer.consumer_id
