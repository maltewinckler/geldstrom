"""Readiness value object and query for the gateway application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, computed_field

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory
    from gateway.application.ports.gateway_readiness_service import GatewayReadinessPort


class ReadinessStatus(BaseModel):
    """Immutable snapshot of gateway readiness sub-checks."""

    model_config = {"frozen": True}

    db: bool
    product_key: bool
    catalog: bool
    redis: bool

    @computed_field
    @property
    def is_ready(self) -> bool:
        return self.db and self.product_key and self.catalog and self.redis


class GetReadinessQuery:
    """Return the current readiness status of the gateway."""

    def __init__(self, readiness_service: GatewayReadinessPort) -> None:
        self._service = readiness_service

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(factory.readiness_service)

    async def __call__(self) -> ReadinessStatus:
        return await self._service.check()
