"""Result DTO for the bank metadata lookup query."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel

from gateway.domain.banking_gateway import FinTSInstitute


class BankInfoEnvelope(BaseModel, frozen=True):
    """Application result carrying public bank metadata for a given BLZ."""

    blz: str
    bic: str | None
    name: str
    organization: str | None
    is_fints_capable: bool

    @classmethod
    def from_institute(cls, institute: FinTSInstitute) -> Self:
        return cls(
            blz=str(institute.blz),
            bic=institute.bic,
            name=institute.name,
            organization=institute.organization,
            is_fints_capable=institute.is_pin_tan_capable(),
        )
