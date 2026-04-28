"""FinTS institute aggregate and selection policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from gateway_admin.domain.errors import DomainError
from gateway_admin.domain.value_objects.institutes import (
    BankLeitzahl,
    Bic,
    InstituteEndpoint,
)


@dataclass
class FinTSInstitute:
    """Canonical operational institute data selected from the source CSV."""

    blz: BankLeitzahl
    bic: Bic | None
    name: str
    city: str | None
    organization: str | None
    pin_tan_url: InstituteEndpoint | None
    fints_version: str | None
    last_source_update: date | None
    source_row_checksum: str
    source_payload: dict[str, Any]

    def is_pin_tan_capable(self) -> bool:
        return self.pin_tan_url is not None


class InstituteSelectionPolicy:
    """Resolves multiple source rows into one canonical institute per BLZ."""

    @staticmethod
    def select(candidates: list[FinTSInstitute]) -> FinTSInstitute:
        if not candidates:
            raise DomainError(
                "InstituteSelectionPolicy requires at least one candidate"
            )

        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: (
                0 if candidate.is_pin_tan_capable() else 1,
                -(candidate.last_source_update.toordinal())
                if candidate.last_source_update is not None
                else 0,
                candidate.source_row_checksum,
            ),
        )
        return ranked_candidates[0]
