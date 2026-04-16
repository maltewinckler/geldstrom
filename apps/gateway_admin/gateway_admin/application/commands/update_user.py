"""Update mutable user metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.value_objects.user import Email, UserId

from ..dtos.user import UserSummary, to_user_summary

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class UpdateUserCommand:
    """Update non-secret mutable fields of one user."""

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
        await self._gateway.notify_user_updated(str(user.user_id))
        return to_user_summary(user)
