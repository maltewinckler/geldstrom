"""List sanitized user summaries for operators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from ..dtos.user import UserSummary, to_user_summary

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class ListUsersQuery:
    """Return all users without exposing secret material."""

    def __init__(self, repository) -> None:
        self._repository = repository

    @classmethod
    def from_factory(cls, factory: AdminFactory) -> Self:
        return cls(factory.repos.users)

    async def __call__(self) -> list[UserSummary]:
        users = await self._repository.list_all()
        return [to_user_summary(user) for user in users]
