"""Rotate API keys for existing users."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.domain.entities.users import UserStatus
from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.services.api_key import AdminApiKeyService
from gateway_admin.domain.services.email import EmailService
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.services.identity import IdProvider
from gateway_admin.domain.value_objects.user import UserId

from ..dtos.user import UserKeyResult, to_user_summary

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class RotateUserKeyCommand:
    """Replace one user's API key hash and send the new raw key via email."""

    def __init__(
        self,
        repository,
        gateway: GatewayNotificationService,
        api_key_service: AdminApiKeyService,
        id_provider: IdProvider,
        email_service: EmailService,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._api_key_service = api_key_service
        self._id_provider = id_provider
        self._email_service = email_service

    @classmethod
    def from_factory(
        cls,
        repo_factory: AdminRepositoryFactory,
        service_factory: ServiceFactory,
    ) -> Self:
        return cls(
            repository=repo_factory.users,
            gateway=service_factory.gateway_notifications,
            api_key_service=service_factory.api_key_service,
            id_provider=service_factory.id_provider,
            email_service=service_factory.email_service,
        )

    async def __call__(self, user_id: str) -> UserKeyResult:
        user = await self._repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise ValidationError(f"No user found for id {user_id}")
        if user.status is UserStatus.DELETED:
            raise ValidationError("Deleted users cannot rotate keys")

        raw_key = self._api_key_service.generate(str(user.user_id))
        user.api_key_hash = self._api_key_service.hash(raw_key)
        user.rotated_at = self._id_provider.now()
        await self._repository.save(user)
        await self._gateway.notify_user_updated(str(user.user_id))
        await self._email_service.send_token_email(user.email.value, raw_key)
        return UserKeyResult(user=to_user_summary(user), raw_api_key=raw_key)
