"""Tests for HTTP authentication dependencies."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateway.application.auth.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.presentation.http.dependencies import (
    get_api_key,
    get_authenticated_consumer,
)

# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------


def test_get_api_key_raises_401_when_no_header() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_api_key(credentials=None))
    assert exc_info.value.status_code == 401


def test_get_api_key_returns_token() -> None:
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="my-key")
    result = asyncio.run(get_api_key(credentials=creds))
    assert result == "my-key"


# ---------------------------------------------------------------------------
# get_authenticated_consumer
# ---------------------------------------------------------------------------


def _make_use_case(raises=None, returns=None):
    use_case = AsyncMock()
    if raises:
        use_case.side_effect = raises
    else:
        use_case.return_value = returns
    return use_case


def test_get_authenticated_consumer_returns_identity() -> None:
    from uuid import uuid4

    from gateway.domain.banking_gateway import AuthenticatedConsumer
    from gateway.domain.consumer_access import ConsumerId

    consumer = AuthenticatedConsumer(consumer_id=ConsumerId(uuid4()))
    use_case = _make_use_case(returns=consumer)
    mock_factory = MagicMock()

    with patch.object(AuthenticateConsumerQuery, "from_factory", return_value=use_case):
        result = asyncio.run(
            get_authenticated_consumer(api_key="good-key", factory=mock_factory)
        )
    assert result is consumer


def test_get_authenticated_consumer_raises_401_for_bad_key() -> None:
    from fastapi import HTTPException

    use_case = _make_use_case(raises=UnauthorizedError("Invalid API key"))
    mock_factory = MagicMock()

    with patch.object(AuthenticateConsumerQuery, "from_factory", return_value=use_case):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                get_authenticated_consumer(api_key="bad-key", factory=mock_factory)
            )
    assert exc_info.value.status_code == 401


def test_get_authenticated_consumer_raises_403_for_disabled_consumer() -> None:
    from fastapi import HTTPException

    use_case = _make_use_case(raises=ForbiddenError("Consumer is disabled"))
    mock_factory = MagicMock()

    with patch.object(AuthenticateConsumerQuery, "from_factory", return_value=use_case):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                get_authenticated_consumer(api_key="key", factory=mock_factory)
            )
    assert exc_info.value.status_code == 403
