"""FinTS institute domain model, value objects, and selection policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlparse

from .errors import DomainError

_BLZ_PATTERN = re.compile(r"^\d{8}$")
_BIC_PATTERN = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")


@dataclass(frozen=True)
class BankLeitzahl:
    """German bank routing number."""

    value: str

    def __post_init__(self) -> None:
        if not _BLZ_PATTERN.match(self.value):
            raise DomainError("BankLeitzahl must be an 8-digit string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SkippedRow:
    """A CSV row that had a valid BLZ but could not be fully parsed."""

    blz: str
    name: str
    reason: str


@dataclass(frozen=True)
class Bic:
    """Bank identifier code."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _BIC_PATTERN.match(normalized):
            raise DomainError("Bic must be 8 or 11 alphanumeric characters")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class InstituteEndpoint:
    """PIN/TAN endpoint URL used by the banking connector."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise DomainError("InstituteEndpoint must be an https URL")

    def __str__(self) -> str:
        return self.value


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
