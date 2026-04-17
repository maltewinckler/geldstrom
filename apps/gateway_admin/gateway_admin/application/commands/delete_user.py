"""Delete users administratively."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.application.dtos.user import UserSummary, to_user_summary
from gateway_admin.domain.entities.users import UserStatus
from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.value_objects.user import UserId

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class DeleteUserCommand:
    """Mark one user as deleted and clear retained key material."""

    def __init__(self, repository, gateway: GatewayNotificationService) -> None:
        self._repository = repository
        self._gateway = gateway

    @classmethod
    def from_factory(
        cls,
        repo_factory: AdminRepositoryFactory,
        service_factory: ServiceFactory,
    ) -> Self:
        return cls(
            repository=repo_factory.users,
            gateway=service_factory.gateway_notifications,
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
        await self._gateway.notify_user_updated(str(user.user_id))
        return to_user_summary(user)
