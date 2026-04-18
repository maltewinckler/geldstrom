"""Tests for POST /admin/catalog/sync API endpoint."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from hypothesis import event, given, settings
from hypothesis import strategies as st

from gateway_admin.application.dtos.institute_catalog import InstituteCatalogSyncResult
from gateway_admin.infrastructure.services.email_service import MockEmailService
from gateway_admin.presentation.api.dependencies import (
    get_repo_factory,
    get_service_factory,
)
from gateway_admin.presentation.api.main import app

from .conftest import (
    InMemoryUserRepository,
    MockAdminRepositoryFactory,
    MockServiceFactory,
)


def _override_deps(repo_factory, svc_factory) -> None:
    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_catalog_no_file_returns_422(client: AsyncClient) -> None:
    """POST /admin/catalog/sync with no file attached returns HTTP 422.

    Validates: Requirements 1.3
    """
    response = await client.post("/admin/catalog/sync")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Property 1: Valid CSV upload returns well-formed success response
# Validates: Requirements 1.1
# ---------------------------------------------------------------------------

_valid_csv_content = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
).map(lambda body: f"blz,name\n{body}")

_non_negative_int = st.integers(min_value=0, max_value=10_000)


@settings(max_examples=100)
@given(
    csv_content=_valid_csv_content,
    loaded=_non_negative_int,
    skipped=_non_negative_int,
)
def test_valid_csv_upload_returns_well_formed_success_response(
    csv_content: str,
    loaded: int,
    skipped: int,
) -> None:
    """For any valid CSV content, POST /admin/catalog/sync returns HTTP 200
    with non-negative integer fields loaded_count and skipped_count.

    Tag: Feature: fints-institute-csv-upload, Property 1: valid CSV upload returns well-formed success response
    **Validates: Requirements 1.1**
    """
    event(
        "Feature: fints-institute-csv-upload, Property 1: valid CSV upload returns well-formed success response"
    )
    mock_result = InstituteCatalogSyncResult(
        loaded_count=loaded,
        skipped_rows=tuple(object() for _ in range(skipped)),  # type: ignore[arg-type]
    )
    mock_command_instance = AsyncMock(return_value=mock_result)
    mock_command_cls = MagicMock()
    mock_command_cls.from_factory.return_value = mock_command_instance

    repo_factory = MockAdminRepositoryFactory(user_repo=InMemoryUserRepository())
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    _override_deps(repo_factory, svc_factory)
    try:
        with patch(
            "gateway_admin.presentation.api.routes.SyncInstituteCatalogCommand",
            mock_command_cls,
        ):

            async def _run():
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as ac:
                    return await ac.post(
                        "/admin/catalog/sync",
                        files={
                            "file": ("upload.csv", csv_content.encode(), "text/csv")
                        },
                    )

            response = asyncio.run(_run())
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["loaded_count"], int)
    assert isinstance(body["skipped_count"], int)
    assert body["loaded_count"] >= 0
    assert body["skipped_count"] >= 0


# ---------------------------------------------------------------------------
# Property 2: Non-CSV filename is rejected with HTTP 400
# Validates: Requirements 1.2
# ---------------------------------------------------------------------------

_non_csv_filename = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
).filter(lambda name: not name.endswith(".csv"))


@settings(max_examples=100)
@given(filename=_non_csv_filename)
def test_non_csv_filename_is_rejected_with_http_400(filename: str) -> None:
    """For any filename that does not end in .csv, POST /admin/catalog/sync
    returns HTTP 400 with a non-empty detail field.

    Tag: Feature: fints-institute-csv-upload, Property 2: non-CSV filename is rejected with HTTP 400
    **Validates: Requirements 1.2**
    """
    event(
        "Feature: fints-institute-csv-upload, Property 2: non-CSV filename is rejected with HTTP 400"
    )
    repo_factory = MockAdminRepositoryFactory(user_repo=InMemoryUserRepository())
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    _override_deps(repo_factory, svc_factory)
    try:

        async def _run():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    "/admin/catalog/sync",
                    files={"file": (filename, b"some,content\n", "text/plain")},
                )

        response = asyncio.run(_run())
    finally:
        _clear_overrides()

    assert response.status_code == 400
    body = response.json()
    assert isinstance(body.get("detail"), str)
    assert len(body["detail"]) > 0


# ---------------------------------------------------------------------------
# Property 3: Command exception maps to HTTP 500 with detail
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------

_exception_message = st.text(min_size=1)


@settings(max_examples=100)
@given(message=_exception_message)
def test_command_exception_maps_to_http_500_with_detail(message: str) -> None:
    """For any exception message raised by SyncInstituteCatalogCommand, POST
    /admin/catalog/sync returns HTTP 500 with a JSON body whose detail field
    contains the exception message.

    Tag: Feature: fints-institute-csv-upload, Property 3: command exception maps to HTTP 500 with detail
    **Validates: Requirements 1.4**
    """
    event(
        "Feature: fints-institute-csv-upload, Property 3: command exception maps to HTTP 500 with detail"
    )
    mock_command_instance = AsyncMock(side_effect=Exception(message))
    mock_command_cls = MagicMock()
    mock_command_cls.from_factory.return_value = mock_command_instance

    repo_factory = MockAdminRepositoryFactory(user_repo=InMemoryUserRepository())
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    _override_deps(repo_factory, svc_factory)
    try:
        with patch(
            "gateway_admin.presentation.api.routes.SyncInstituteCatalogCommand",
            mock_command_cls,
        ):

            async def _run():
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as ac:
                    return await ac.post(
                        "/admin/catalog/sync",
                        files={"file": ("upload.csv", b"blz,name\n", "text/csv")},
                    )

            response = asyncio.run(_run())
    finally:
        _clear_overrides()

    assert response.status_code == 500
    body = response.json()
    assert isinstance(body.get("detail"), str)
    assert message in body["detail"]
