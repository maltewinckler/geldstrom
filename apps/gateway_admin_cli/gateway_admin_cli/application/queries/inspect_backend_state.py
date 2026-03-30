"""Inspect sanitized backend state for operators."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self

from gateway_admin_cli.domain.institutes import BankLeitzahl
from gateway_admin_cli.domain.users import UserStatus

from ..dtos.backend_state import BackendStateReport
from ..dtos.product_registration import to_product_registration_summary

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


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
    def from_factory(cls, factory: AdminFactory) -> Self:
        return cls(
            user_repository=factory.repos.users,
            institute_repository=factory.repos.institutes,
            product_registration_repository=factory.repos.product_registration,
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
