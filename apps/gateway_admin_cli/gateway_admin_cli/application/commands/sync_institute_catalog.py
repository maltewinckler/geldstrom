"""Synchronize the canonical institute catalog from CSV input."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Self

from gateway_admin_cli.domain.institutes import InstituteSelectionPolicy

from ..dtos.institute_catalog import InstituteCatalogSyncResult

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class SyncInstituteCatalogCommand:
    """Read, canonicalize, persist, and invalidate the institute catalog."""

    def __init__(
        self,
        csv_reader,
        repository,
        institute_cache_loader,
    ) -> None:
        self._csv_reader = csv_reader
        self._repository = repository
        self._institute_cache_loader = institute_cache_loader

    @classmethod
    def from_factory(cls, factory: AdminFactory) -> Self:
        return cls(
            csv_reader=factory.institute_csv_reader,
            repository=factory.repos.institutes,
            institute_cache_loader=factory.institute_cache_loader,
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
        await self._institute_cache_loader.load(canonical_institutes)
        return InstituteCatalogSyncResult(
            loaded_count=len(canonical_institutes),
            skipped_rows=tuple(skipped_rows),
        )
