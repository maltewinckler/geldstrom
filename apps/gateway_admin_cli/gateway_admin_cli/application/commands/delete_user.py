"""Delete users administratively."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin_cli.domain.errors import ValidationError
from gateway_admin_cli.domain.users import UserId

from ..dtos.user import UserSummary, to_user_summary

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class DeleteUserCommand:
    """Mark one user as deleted and clear retained key material."""

    def __init__(self, repository, user_cache_writer) -> None:
        self._repository = repository
        self._user_cache_writer = user_cache_writer

    @classmethod
    def from_factory(cls, factory: AdminFactory) -> Self:
        return cls(
            repository=factory.repos.users,
            user_cache_writer=factory.user_cache_writer,
        )

    async def __call__(self, user_id: str) -> UserSummary:
        user = await self._repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise ValidationError(f"No user found for id {user_id}")

        user.mark_deleted()
        user.api_key_hash = None
        await self._repository.save(user)
        await self._user_cache_writer.reload_one(user)
        return to_user_summary(user)
