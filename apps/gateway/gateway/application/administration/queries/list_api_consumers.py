"""List sanitized API consumer summaries for operators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway.domain.consumer_access import ApiConsumerRepository

from ..dtos.api_consumer import ApiConsumerSummary, to_consumer_summary

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class ListApiConsumersQuery:
    """Return all API consumers without exposing secret material."""

    def __init__(self, repository: ApiConsumerRepository) -> None:
        self._repository = repository

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(factory.repos.consumer)

    async def __call__(self) -> list[ApiConsumerSummary]:
        consumers = await self._repository.list_all()
        return [to_consumer_summary(consumer) for consumer in consumers]
