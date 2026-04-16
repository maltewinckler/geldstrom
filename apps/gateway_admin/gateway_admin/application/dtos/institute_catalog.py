"""Institute catalog sync result DTO."""

from __future__ import annotations

from dataclasses import dataclass, field

from gateway_admin.domain.value_objects.institutes import SkippedRow


@dataclass(frozen=True)
class InstituteCatalogSyncResult:
    """Outcome of syncing the canonical institute catalog."""

    loaded_count: int
    skipped_rows: tuple[SkippedRow, ...] = field(default_factory=tuple)
