"""Create users for administrative workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway_admin_cli.domain.errors import ValidationError
from gateway_admin_cli.domain.users import Email, User, UserId, UserStatus

from ..dtos.user import UserKeyResult, to_user_summary

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class CreateUserCommand:
    """Create one active user and reveal the raw API key once."""

    def __init__(
        self,
        repository,
        user_cache_writer,
        api_key_service,
        id_provider,
    ) -> None:
        self._repository = repository
        self._user_cache_writer = user_cache_writer
        self._api_key_service = api_key_service
        self._id_provider = id_provider

    @classmethod
    def from_factory(cls, factory: AdminFactory) -> Self:
        return cls(
            repository=factory.repos.users,
            user_cache_writer=factory.user_cache_writer,
            api_key_service=factory.api_key_service,
            id_provider=factory.id_provider,
        )

    async def __call__(self, email: str) -> UserKeyResult:
        normalized_email = Email(email)
        existing = await self._repository.get_by_email(normalized_email)
        if existing is not None:
            raise ValidationError(
                f"User with email {normalized_email.value} already exists"
            )

        raw_key = self._api_key_service.generate()
        user = User(
            user_id=UserId(UUID(self._id_provider.new_operation_id())),
            email=normalized_email,
            api_key_hash=self._api_key_service.hash(raw_key),
            status=UserStatus.ACTIVE,
            created_at=self._id_provider.now(),
        )
        await self._repository.save(user)
        await self._user_cache_writer.reload_one(user)
        return UserKeyResult(
            user=to_user_summary(user),
            raw_api_key=raw_key,
        )
