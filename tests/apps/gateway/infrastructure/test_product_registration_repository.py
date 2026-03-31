"""Integration tests for the SQL product registration repository."""

from __future__ import annotations

from gateway.infrastructure.persistence.sql import (
    SQLFinTSProductRegistrationRepository,
)


def test_product_registration_repository_get_current_returns_none_when_empty(
    postgres_engine, async_runner
) -> None:
    repository = SQLFinTSProductRegistrationRepository(postgres_engine)

    loaded = async_runner(repository.get_current())

    assert loaded is None
