"""Tests for HTTP authentication dependencies."""

from __future__ import annotations

import asyncio

import pytest

from gateway.presentation.http.dependencies import get_api_key


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
