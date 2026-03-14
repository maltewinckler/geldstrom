"""Synchronize the canonical institute catalog from CSV input."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Self

from gateway.domain.institution_catalog import (
    FinTSInstituteRepository,
    InstituteSelectionPolicy,
)

from ..dtos.institute_catalog import InstituteCatalogSyncResult
from ..ports.institute_cache import InstituteCacheLoader
from ..ports.institute_csv_reader import InstituteCsvReaderPort

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class SyncInstituteCatalogCommand:
    """Read, canonicalize, persist, and warm the institute catalog."""

    def __init__(
        self,
        csv_reader: InstituteCsvReaderPort,
        repository: FinTSInstituteRepository,
        institute_cache: InstituteCacheLoader,
    ) -> None:
        self._csv_reader = csv_reader
        self._repository = repository
        self._institute_cache = institute_cache

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            csv_reader=factory.institute_csv_reader,
            repository=factory.repos.institute,
            institute_cache=factory.caches.institute,
        )

    async def __call__(self, csv_path: Path) -> InstituteCatalogSyncResult:
        raw_institutes = self._csv_reader.read(csv_path)
        grouped: dict[str, list] = defaultdict(list)
        for institute in raw_institutes:
            grouped[institute.blz.value].append(institute)

        canonical_institutes = [
            InstituteSelectionPolicy.select(candidates)
            for _, candidates in sorted(grouped.items())
        ]
        await self._repository.replace_catalog(canonical_institutes)
        await self._institute_cache.load(canonical_institutes)
        return InstituteCatalogSyncResult(loaded_count=len(canonical_institutes))
