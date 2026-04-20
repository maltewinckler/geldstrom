"""Unit tests for GetProductRegistrationQuery.

Covers:
- Returns the ProductRegistration entity when the repository has a row (Req 1.2)
- Returns None when the repository has no row (Req 1.3)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from gateway_admin.application.queries.get_product_registration import (
    GetProductRegistrationQuery,
)
from gateway_admin.domain.entities.product import ProductRegistration


@pytest.mark.asyncio
async def test_get_product_registration_returns_entity_when_row_exists() -> None:
    """__call__ returns the ProductRegistration entity when the repository has a row.

    Validates: Requirement 1.2
    """
    entity = ProductRegistration(
        product_key="PROD-KEY-123",
        product_version="1.0",
        updated_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
    )
    repo = AsyncMock()
    repo.get_current.return_value = entity

    query = GetProductRegistrationQuery(repository=repo)
    result = await query()

    assert result is entity
    repo.get_current.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_product_registration_returns_none_when_absent() -> None:
    """__call__ returns None when the repository has no row.

    Validates: Requirement 1.3
    """
    repo = AsyncMock()
    repo.get_current.return_value = None

    query = GetProductRegistrationQuery(repository=repo)
    result = await query()

    assert result is None
    repo.get_current.assert_awaited_once()
