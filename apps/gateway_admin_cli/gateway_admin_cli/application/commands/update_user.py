"""Update mutable user metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin_cli.domain.errors import ValidationError
from gateway_admin_cli.domain.users import Email, UserId

from ..dtos.user import UserSummary, to_user_summary

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class UpdateUserCommand:
    """Update non-secret mutable fields of one user."""

    def __init__(self, repository, user_cache_writer) -> None:
        self._repository = repository
        self._user_cache_writer = user_cache_writer

    @classmethod
    def from_factory(cls, factory: AdminFactory) -> Self:
        return cls(
            repository=factory.repos.users,
            user_cache_writer=factory.user_cache_writer,
        )

    async def __call__(self, user_id: str, *, email: str) -> UserSummary:
        user = await self._repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise ValidationError(f"No user found for id {user_id}")

        normalized_email = Email(email)
        existing = await self._repository.get_by_email(normalized_email)
        if existing is not None and existing.user_id != user.user_id:
            raise ValidationError(
                f"User with email {normalized_email.value} already exists"
            )

        user.email = normalized_email
        await self._repository.save(user)
        await self._user_cache_writer.reload_one(user)
        return to_user_summary(user)
