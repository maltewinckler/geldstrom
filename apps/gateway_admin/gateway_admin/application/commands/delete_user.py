"""Delete users administratively."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.application.dtos.user import UserSummary, to_user_summary
from gateway_admin.domain.entities.users import UserStatus
from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.value_objects.user import UserId

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class DeleteUserCommand:
    """Mark one user as deleted and clear retained key material."""

    def __init__(self, repository) -> None:
        self._repository = repository

    @classmethod
    def from_factory(
        cls,
        repo_factory: AdminRepositoryFactory,
        _service_factory: ServiceFactory,
    ) -> Self:
        return cls(
            repository=repo_factory.users,
        )

    async def __call__(self, user_id: str) -> UserSummary:
        user = await self._repository.get_by_id(UserId.from_string(user_id))
        if user is None:
            raise ValidationError(f"No user found for id {user_id}")
        if user.status is UserStatus.DELETED:
            raise ValidationError("User has already been deleted")

        user.mark_deleted()
        user.api_key_hash = None
        await self._repository.save(user)
        return to_user_summary(user)
