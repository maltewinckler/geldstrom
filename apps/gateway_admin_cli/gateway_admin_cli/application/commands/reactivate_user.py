"""Reactivate a previously disabled user account."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin_cli.domain.errors import ValidationError
from gateway_admin_cli.domain.users import UserId, UserStatus

from ..dtos.user import UserKeyResult, to_user_summary

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class ReactivateUserCommand:
    """Re-enable a disabled user, assign a fresh API key, and refresh the auth cache."""

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

    async def __call__(self, user_id: str) -> UserKeyResult:
        user = await self._repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise ValidationError(f"No user found for id {user_id}")
        if user.status is UserStatus.DELETED:
            raise ValidationError("Deleted users cannot be reactivated")
        if user.status is UserStatus.ACTIVE:
            raise ValidationError("User is already active")

        raw_key = self._api_key_service.generate()
        api_key_hash = self._api_key_service.hash(raw_key)
        user.reactivate(api_key_hash)
        user.rotated_at = self._id_provider.now()
        await self._repository.save(user)
        await self._user_cache_writer.reload_one(user)
        return UserKeyResult(
            user=to_user_summary(user),
            raw_api_key=raw_key,
        )
