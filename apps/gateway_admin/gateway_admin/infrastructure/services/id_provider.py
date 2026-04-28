"""Runtime identity and time provider - implements IdProvider port."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self
from uuid import uuid4

from gateway_admin.domain.services.identity import IdProvider

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class RuntimeIdProvider(IdProvider):
    """Provides UUIDs and UTC timestamps at runtime."""

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:  # noqa: ARG003
        return cls()

    def new_operation_id(self) -> str:
        return str(uuid4())

    def now(self) -> datetime:
        return datetime.now(UTC)
