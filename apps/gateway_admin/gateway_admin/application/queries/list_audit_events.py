"""List audit events for operators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.domain.audit import AuditPage, AuditQuery, AuditQueryRepository

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class ListAuditEventsQuery:
    """Return a paginated, filtered list of audit events."""

    def __init__(self, repo: AuditQueryRepository) -> None:
        self._repo = repo

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(repo_factory.audit)

    async def __call__(self, q: AuditQuery) -> AuditPage:
        return await self._repo.query(q)
