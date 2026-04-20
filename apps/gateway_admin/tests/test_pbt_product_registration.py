"""Property-based tests for GET/PUT /admin/product-registration API endpoints.

Feature: fints-product-config
Property 1: Product registration round-trip
Property 2: Whitespace-only fields are rejected
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from hypothesis import given, settings
from hypothesis import strategies as st

from gateway_admin.infrastructure.services.email_service import MockEmailService
from gateway_admin.presentation.api.dependencies import (
    get_repo_factory,
    get_service_factory,
)
from gateway_admin.presentation.api.main import app

from .conftest import MockServiceFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_valid_text = st.text(min_size=1).filter(lambda s: s.strip())


def _make_repo_factory(saved_registration_holder: list) -> MagicMock:
    """Build a mock repo factory that saves to and reads from a shared holder list."""
    product_repo = AsyncMock()

    async def _save_current(registration):
        saved_registration_holder.clear()
        saved_registration_holder.append(registration)

    async def _get_current():
        return saved_registration_holder[0] if saved_registration_holder else None

    product_repo.save_current.side_effect = _save_current
    product_repo.get_current.side_effect = _get_current

    repo_factory = MagicMock()
    repo_factory.product_registration = product_repo
    return repo_factory


# ---------------------------------------------------------------------------
# Property 1: Product registration round-trip
# ---------------------------------------------------------------------------


@given(
    product_key=_valid_text,
    product_version=_valid_text,
)
@settings(max_examples=100)
def test_property_1_product_registration_round_trip(
    product_key: str,
    product_version: str,
) -> None:
    """For any valid (non-empty, non-whitespace-only) product_key and product_version,
    a successful PUT followed by GET returns the same stripped values and a valid
    updated_at ISO 8601 timestamp.

    Validates: Requirements 1.2, 2.2
    """
    saved: list = []
    repo_factory = _make_repo_factory(saved)
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory
    try:

        async def _run() -> tuple[int, int, dict]:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                put_response = await client.put(
                    "/admin/product-registration",
                    json={
                        "product_key": product_key,
                        "product_version": product_version,
                    },
                )
                get_response = await client.get("/admin/product-registration")
            return (
                put_response.status_code,
                get_response.status_code,
                get_response.json(),
            )

        put_status, get_status, get_body = asyncio.run(_run())
    finally:
        app.dependency_overrides.clear()

    # PUT must succeed
    assert put_status == 200, f"PUT returned {put_status}, expected 200"

    # GET must succeed
    assert get_status == 200, f"GET returned {get_status}, expected 200"

    # Returned values must equal the stripped inputs
    assert get_body["product_key"] == product_key.strip()
    assert get_body["product_version"] == product_version.strip()

    # updated_at must be a valid ISO 8601 timestamp
    updated_at_str = get_body.get("updated_at")
    assert updated_at_str is not None, "updated_at missing from GET response"
    parsed = datetime.fromisoformat(updated_at_str)
    assert isinstance(parsed, datetime)


# ---------------------------------------------------------------------------
# Property 2: Whitespace-only fields are rejected
# ---------------------------------------------------------------------------

_whitespace_text = st.from_regex(r"[\s]+", fullmatch=True)


@given(
    whitespace_key=_whitespace_text,
    valid_version=_valid_text,
)
@settings(max_examples=100)
def test_property_2_whitespace_only_product_key_rejected(
    whitespace_key: str,
    valid_version: str,
) -> None:
    """For any string composed entirely of whitespace characters used as product_key,
    the PUT endpoint returns HTTP 422 with a detail field.

    Validates: Requirements 2.3, 2.4
    """
    saved: list = []
    repo_factory = _make_repo_factory(saved)
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory
    try:

        async def _run() -> tuple[int, dict]:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.put(
                    "/admin/product-registration",
                    json={
                        "product_key": whitespace_key,
                        "product_version": valid_version,
                    },
                )
            return response.status_code, response.json()

        status, body = asyncio.run(_run())
    finally:
        app.dependency_overrides.clear()

    assert status == 422, (
        f"PUT returned {status}, expected 422 for whitespace-only product_key"
    )
    assert "detail" in body, f"Response body missing 'detail' field: {body}"


@given(
    valid_key=_valid_text,
    whitespace_version=_whitespace_text,
)
@settings(max_examples=100)
def test_property_2_whitespace_only_product_version_rejected(
    valid_key: str,
    whitespace_version: str,
) -> None:
    """For any string composed entirely of whitespace characters used as product_version,
    the PUT endpoint returns HTTP 422 with a detail field.

    Validates: Requirements 2.3, 2.4
    """
    saved: list = []
    repo_factory = _make_repo_factory(saved)
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory
    try:

        async def _run() -> tuple[int, dict]:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.put(
                    "/admin/product-registration",
                    json={
                        "product_key": valid_key,
                        "product_version": whitespace_version,
                    },
                )
            return response.status_code, response.json()

        status, body = asyncio.run(_run())
    finally:
        app.dependency_overrides.clear()

    assert status == 422, (
        f"PUT returned {status}, expected 422 for whitespace-only product_version"
    )
    assert "detail" in body, f"Response body missing 'detail' field: {body}"
