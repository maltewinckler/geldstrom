"""Domain services for institution catalog canonicalization."""

from __future__ import annotations

from gateway.domain.shared import DomainError

from .model import FinTSInstitute


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
