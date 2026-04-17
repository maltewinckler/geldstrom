"""Inspect sanitized backend state for operators."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self

from gateway_admin.application.dtos.backend_state import BackendStateReport
from gateway_admin.application.dtos.product_registration import (
    to_product_registration_summary,
)
from gateway_admin.domain.entities.users import UserStatus
from gateway_admin.domain.value_objects.institutes import BankLeitzahl

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class InspectBackendStateQuery:
    """Collect a sanitized snapshot of database state for operator inspection."""

    def __init__(
        self,
        user_repository,
        institute_repository,
        product_registration_repository,
    ) -> None:
        self._user_repository = user_repository
        self._institute_repository = institute_repository
        self._product_registration_repository = product_registration_repository

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(
            user_repository=repo_factory.users,
            institute_repository=repo_factory.institutes,
            product_registration_repository=repo_factory.product_registration,
        )

    async def __call__(self, *, blz: str | None = None) -> BackendStateReport:
        users, institutes, registration = await asyncio.gather(
            self._user_repository.list_all(),
            self._institute_repository.list_all(),
            self._product_registration_repository.get_current(),
        )
        selected_institute = (
            await self._institute_repository.get_by_blz(BankLeitzahl(blz))
            if blz is not None
            else None
        )
        return BackendStateReport(
            db_connectivity="ok",
            total_user_count=len(users),
            active_user_count=sum(
                1 for user in users if user.status is UserStatus.ACTIVE
            ),
            institute_count=len(institutes),
            selected_institute=selected_institute,
            product_registration=(
                to_product_registration_summary(registration)
                if registration is not None
                else None
            ),
        )
