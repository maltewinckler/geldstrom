"""Unit tests for GET /admin/product-registration API endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from gateway_admin.infrastructure.services.email_service import MockEmailService
from gateway_admin.presentation.api.dependencies import (
    get_repo_factory,
    get_service_factory,
)
from gateway_admin.presentation.api.main import app, lifespan

from .conftest import MockServiceFactory


def _make_repo_factory_with_product_registration(return_value):
    """Build a mock repo factory whose product_registration.get_current returns the given value."""
    product_repo = AsyncMock()
    product_repo.get_current.return_value = return_value

    repo_factory = MagicMock()
    repo_factory.product_registration = product_repo
    return repo_factory


@pytest.mark.asyncio
async def test_get_product_registration_returns_404_when_no_registration_exists() -> (
    None
):
    """GET /admin/product-registration returns 404 with a detail field when no registration exists.

    Validates: Requirements 1.3, 5.2
    """
    repo_factory = _make_repo_factory_with_product_registration(None)
    svc_factory = MockServiceFactory(email_svc=MockEmailService())

    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/product-registration")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_put_product_registration_triggers_notify_product_registration_updated() -> (
    None
):
    """PUT /admin/product-registration returns 200 and calls notify_product_registration_updated.

    Validates: Requirement 2.5
    """
    # Repo mock: save_current succeeds silently
    product_repo = AsyncMock()
    product_repo.save_current.return_value = None

    repo_factory = MagicMock()
    repo_factory.product_registration = product_repo

    # Service mock: gateway_notifications with a trackable notify method
    gateway_notifications = AsyncMock()
    svc_factory = MagicMock()
    svc_factory.gateway_notifications = gateway_notifications
    svc_factory.id_provider = MockServiceFactory(
        email_svc=MockEmailService()
    ).id_provider

    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/admin/product-registration",
                json={"product_key": "test-key-123", "product_version": "1.0"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    gateway_notifications.notify_product_registration_updated.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_starts_successfully_with_empty_product_registration_table() -> (
    None
):
    """Admin API starts without error when fints_product_registration table is empty.

    Validates: Requirement 5.1
    """
    # Patch InitializeDatabaseCommand so no real DB connection is needed.
    # The lifespan must complete without raising even when no ProductRegistration
    # row exists — the startup sequence no longer requires one.
    noop_cmd = AsyncMock(return_value=None)

    mock_settings = MagicMock()
    mock_settings.admin_ui_port = 8001

    with (
        patch(
            "gateway_admin.presentation.api.main.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "gateway_admin.presentation.api.main.InitializeDatabaseCommand.from_factory",
            return_value=noop_cmd,
        ),
        patch(
            "gateway_admin.presentation.api.main.AdminRepositoryFactorySQLAlchemy"
        ) as mock_repo_cls,
        patch(
            "gateway_admin.presentation.api.main.ServiceFactorySQLAlchemy"
        ) as mock_svc_cls,
    ):
        mock_repo_factory = MagicMock()
        mock_repo_factory.dispose = AsyncMock()
        mock_repo_cls.return_value = mock_repo_factory

        mock_svc_factory = MagicMock()
        mock_svc_cls.from_factory.return_value = mock_svc_factory

        # Run the lifespan — it must not raise
        raised = False
        try:
            async with lifespan(app):
                pass
        except Exception:
            raised = True

    assert not raised, (
        "lifespan raised an exception with an empty product_registration table"
    )
    # Confirm InitializeDatabaseCommand was invoked (startup ran)
    noop_cmd.assert_awaited_once()


@pytest.mark.asyncio
async def test_app_responds_after_startup_with_empty_product_registration_table() -> (
    None
):
    """Admin API handles requests normally when started with no product registration row.

    Validates: Requirement 5.1
    """
    noop_cmd = AsyncMock(return_value=None)

    with (
        patch(
            "gateway_admin.presentation.api.main.InitializeDatabaseCommand.from_factory",
            return_value=noop_cmd,
        ),
        patch(
            "gateway_admin.presentation.api.main.AdminRepositoryFactorySQLAlchemy"
        ) as mock_repo_cls,
        patch(
            "gateway_admin.presentation.api.main.ServiceFactorySQLAlchemy"
        ) as mock_svc_cls,
    ):
        mock_repo_factory = MagicMock()
        mock_repo_factory.dispose = AsyncMock()
        mock_repo_cls.return_value = mock_repo_factory

        mock_svc_factory = MagicMock()
        mock_svc_cls.from_factory.return_value = mock_svc_factory

        # Also override the request-scoped dependencies so the route handler works
        product_repo = AsyncMock()
        product_repo.get_current.return_value = None
        req_repo_factory = MagicMock()
        req_repo_factory.product_registration = product_repo

        req_svc_factory = MockServiceFactory(email_svc=MockEmailService())

        app.dependency_overrides[get_repo_factory] = lambda: req_repo_factory
        app.dependency_overrides[get_service_factory] = lambda: req_svc_factory
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/admin/product-registration")
        finally:
            app.dependency_overrides.clear()

    # App is running — 404 is the expected response when no row exists (Req 1.3)
    assert response.status_code == 404
