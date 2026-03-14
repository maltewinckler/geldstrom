"""Institute catalog sync result DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstituteCatalogSyncResult:
    """Outcome of syncing the canonical institute catalog."""

    loaded_count: int
