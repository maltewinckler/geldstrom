"""Create users for administrative workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway_admin.application.dtos.user import UserKeyResult, to_user_summary
from gateway_admin.domain.entities.users import User, UserStatus
from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.services.api_key import AdminApiKeyService
from gateway_admin.domain.services.email import EmailService
from gateway_admin.domain.services.identity import IdProvider
from gateway_admin.domain.value_objects.user import Email, UserId

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class CreateUserCommand:
    """Create one active user and send the raw API key via email."""

    def __init__(
        self,
        repository,
        api_key_service: AdminApiKeyService,
        id_provider: IdProvider,
        email_service: EmailService,
    ) -> None:
        self._repository = repository
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
            api_key_service=service_factory.api_key_service,
            id_provider=service_factory.id_provider,
            email_service=service_factory.email_service,
        )

    async def __call__(self, email: str) -> UserKeyResult:
        normalized_email = Email(email)
        existing = await self._repository.get_by_email(normalized_email)
        if existing is not None:
            raise ValidationError(
                f"User with email {normalized_email.value} already exists"
            )

        user_id = self._id_provider.new_operation_id()
        raw_key = self._api_key_service.generate(user_id)
        user = User(
            user_id=UserId(UUID(user_id)),
            email=normalized_email,
            api_key_hash=self._api_key_service.hash(raw_key),
            status=UserStatus.ACTIVE,
            created_at=self._id_provider.now(),
        )
        await self._repository.save(user)
        await self._email_service.send_token_email(normalized_email.value, raw_key)
        return UserKeyResult(user=to_user_summary(user), raw_api_key=raw_key)
