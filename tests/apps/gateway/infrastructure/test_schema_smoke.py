"""Smoke tests for schema bootstrap helpers."""

from gateway_contracts.schema import (
    create_test_schema,
    drop_test_schema,
)


def test_schema_helpers_create_and_drop(postgres_engine, async_runner) -> None:
    async_runner(drop_test_schema(postgres_engine))
    async_runner(create_test_schema(postgres_engine))
