"""Synchronize the canonical institute catalog from CSV input."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Self

from gateway_admin.domain.entities.institutes import InstituteSelectionPolicy
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.services.institute_csv import (
    InstituteCsvReaderPort,
)

from ..dtos.institute_catalog import InstituteCatalogSyncResult

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class SyncInstituteCatalogCommand:
    """Read, canonicalize, persist, and notify the gateway."""

    def __init__(
        self,
        csv_reader: InstituteCsvReaderPort,
        repository,
        gateway: GatewayNotificationService,
    ) -> None:
        self._csv_reader = csv_reader
        self._repository = repository
        self._gateway = gateway

    @classmethod
    def from_factory(
        cls,
        repo_factory: AdminRepositoryFactory,
        service_factory: ServiceFactory,
    ) -> Self:
        return cls(
            csv_reader=service_factory.csv_reader,
            repository=repo_factory.institutes,
            gateway=service_factory.gateway_notifications,
        )

    async def __call__(self, csv_path: Path) -> InstituteCatalogSyncResult:
        raw_institutes, skipped_rows = self._csv_reader.read(csv_path)
        grouped: dict[str, list] = defaultdict(list)
        for institute in raw_institutes:
            grouped[institute.blz.value].append(institute)

        canonical_institutes = [
            InstituteSelectionPolicy.select(candidates)
            for _, candidates in sorted(grouped.items())
        ]
        await self._repository.replace_catalog(canonical_institutes)
        await self._gateway.notify_institute_catalog_replaced()
        return InstituteCatalogSyncResult(
            loaded_count=len(canonical_institutes),
            skipped_rows=tuple(skipped_rows),
        )
