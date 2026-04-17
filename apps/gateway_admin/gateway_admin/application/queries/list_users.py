"""List sanitized user summaries for operators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.application.dtos.user import UserSummary, to_user_summary
from gateway_admin.domain.repositories.user_repository import UserQuery

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class UserPageResult:
    """Paginated result of a user list query."""

    def __init__(
        self, users: list[UserSummary], total: int, page: int, page_size: int
    ) -> None:
        self.users = users
        self.total = total
        self.page = page
        self.page_size = page_size


class ListUsersQuery:
    """Return a filtered, paginated list of users without exposing secret material."""

    def __init__(self, repository) -> None:
        self._repository = repository

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(repo_factory.users)

    async def __call__(self, q: UserQuery | None = None) -> UserPageResult:
        q = q or UserQuery()
        page = await self._repository.query(q)
        return UserPageResult(
            users=[to_user_summary(u) for u in page.users],
            total=page.total,
            page=page.page,
            page_size=page.page_size,
        )
