"""Inspect sanitized backend state for operators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway.application.health.queries.evaluate_health import EvaluateHealthQuery
from gateway.domain.consumer_access import ApiConsumerRepository
from gateway.domain.institution_catalog import BankLeitzahl, FinTSInstituteRepository
from gateway.domain.product_registration import FinTSProductRegistrationRepository

from ..dtos.backend_state import BackendStateReport
from ..dtos.product_registration import to_product_registration_summary

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class InspectBackendStateQuery:
    """Collect a sanitized snapshot of health and cache-related backend state."""

    def __init__(
        self,
        evaluate_health: EvaluateHealthQuery,
        consumer_repository: ApiConsumerRepository,
        institute_repository: FinTSInstituteRepository,
        product_registration_repository: FinTSProductRegistrationRepository,
    ) -> None:
        self._evaluate_health = evaluate_health
        self._consumer_repository = consumer_repository
        self._institute_repository = institute_repository
        self._product_registration_repository = product_registration_repository

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            evaluate_health=EvaluateHealthQuery.from_factory(factory),
            consumer_repository=factory.repos.consumer,
            institute_repository=factory.repos.institute,
            product_registration_repository=factory.repos.product_registration,
        )

    async def __call__(
        self, *, blz: BankLeitzahl | None = None
    ) -> BackendStateReport:
        health = await self._evaluate_health.ready()
        consumers = await self._consumer_repository.list_all()
        institutes = await self._institute_repository.list_all()
        registration = await self._product_registration_repository.get_current()
        selected_institute = (
            await self._institute_repository.get_by_blz(blz) if blz is not None else None
        )
        return BackendStateReport(
            health=health,
            total_consumer_count=len(consumers),
            active_consumer_count=sum(
                consumer.status.value == "active" for consumer in consumers
            ),
            institute_count=len(institutes),
            selected_institute=selected_institute,
            product_registration=(
                to_product_registration_summary(registration)
                if registration is not None
                else None
            ),
        )
