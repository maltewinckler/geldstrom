"""Bank metadata lookup through the gateway application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway.application.common import InstitutionNotFoundError, ValidationError
from gateway.domain.banking_gateway import BankLeitzahl
from gateway.domain.errors import DomainError

from ...ports.bank_metadata import BankMetadataPort
from ..dtos.lookup_bank import BankInfoEnvelope

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class LookupBankQuery:
    """Resolve public bank metadata for a given BLZ string."""

    def __init__(self, bank_catalog: BankMetadataPort) -> None:
        self._bank_catalog = bank_catalog

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(bank_catalog=factory.caches.institute)

    async def __call__(self, blz_str: str) -> BankInfoEnvelope:
        try:
            blz = BankLeitzahl(blz_str)
        except DomainError as exc:
            raise ValidationError(str(exc)) from exc

        institute = await self._bank_catalog.get_by_blz(blz)
        if institute is None:
            raise InstitutionNotFoundError(f"No institute found for BLZ {blz_str}")

        return BankInfoEnvelope.from_institute(institute)
