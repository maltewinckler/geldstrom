"""Bank metadata lookup through the gateway application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway.application.banking.dtos.lookup_bank import BankInfoEnvelope
from gateway.application.common import InstitutionNotFoundError, ValidationError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.ports.bank_metadata import BankMetadataPort
from gateway.domain.banking_gateway import BankLeitzahl
from gateway.domain.errors import DomainError

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class LookupBankQuery:
    """Authenticate the caller then resolve public bank metadata for a given BLZ."""

    def __init__(
        self,
        bank_catalog: BankMetadataPort,
        authenticate_consumer: AuthenticateConsumerQuery,
    ) -> None:
        self._bank_catalog = bank_catalog
        self._authenticate_consumer = authenticate_consumer

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            bank_catalog=factory.caches.institute,
            authenticate_consumer=AuthenticateConsumerQuery.from_factory(factory),
        )

    async def __call__(self, blz_str: str, api_key: str) -> BankInfoEnvelope:
        await self._authenticate_consumer(api_key)

        try:
            blz = BankLeitzahl(blz_str)
        except DomainError as exc:
            raise ValidationError(str(exc)) from exc

        institute = await self._bank_catalog.get_by_blz(blz)
        if institute is None:
            raise InstitutionNotFoundError(f"No institute found for BLZ {blz_str}")

        return BankInfoEnvelope.from_institute(institute)
