"""Aggregate for the canonical institution catalog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .value_objects import BankLeitzahl, Bic, InstituteEndpoint


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
