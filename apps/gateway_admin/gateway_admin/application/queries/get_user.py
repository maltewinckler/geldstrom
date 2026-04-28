"""Get a single user by ID."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.application.dtos.user import UserSummary, to_user_summary
from gateway_admin.domain.value_objects.user import UserId

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class GetUserQuery:
    """Return a single user by ID without exposing secret material."""

    def __init__(self, repository) -> None:
        self._repository = repository

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(repo_factory.users)

    async def __call__(self, user_id: str) -> UserSummary | None:
        user = await self._repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            return None
        return to_user_summary(user)
