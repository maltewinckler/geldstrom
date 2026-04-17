"""All-banks catalog query through the gateway application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway.application.banking.dtos.lookup_bank import BankInfoEnvelope
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.ports.bank_catalog import BankCatalogPort

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class ListBanksQuery:
    """Authenticate the caller then return all banks from the catalog."""

    def __init__(
        self,
        bank_catalog: BankCatalogPort,
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

    async def __call__(self, api_key: str) -> list[BankInfoEnvelope]:
        await self._authenticate_consumer(api_key)
        institutes = await self._bank_catalog.list_all()
        return [BankInfoEnvelope.from_institute(inst) for inst in institutes]
