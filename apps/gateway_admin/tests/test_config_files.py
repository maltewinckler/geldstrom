"""Tests asserting config file contents meet requirements."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Repo root is three levels up from this file (tests/ -> gateway_admin/ -> apps/ -> root)
_REPO_ROOT = Path(__file__).parents[3]


def test_admin_settings_instantiates_without_fints_env_vars() -> None:
    """Admin Settings must not require FinTS product env vars to instantiate.

    Validates: Requirements 4.1
    """
    from gateway_admin.config import Settings

    env_without_fints = {
        k: v
        for k, v in os.environ.items()
        if k not in {"FINTS_PRODUCT_REGISTRATION_KEY", "FINTS_PRODUCT_VERSION"}
    }
    env_without_fints.update(
        {
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpassword",
            "GATEWAY_DB_USER": "gwuser",
            "GATEWAY_DB_PASSWORD": "gwpassword",
        }
    )

    with patch.dict(os.environ, env_without_fints, clear=True):
        settings = Settings()

    assert settings is not None
    assert not hasattr(settings, "fints_product_registration_key")
    assert not hasattr(settings, "fints_product_version")


def test_admin_cli_env_example_has_no_fints_product_entries() -> None:
    """config/admin_cli.env.example must not contain FinTS product registration entries.

    Validates: Requirements 4.3
    """
    env_example = _REPO_ROOT / "config" / "admin_cli.env.example"
    content = env_example.read_text()

    assert "FINTS_PRODUCT_REGISTRATION_KEY" not in content, (
        "config/admin_cli.env.example must not contain FINTS_PRODUCT_REGISTRATION_KEY"
    )
    assert "FINTS_PRODUCT_VERSION" not in content, (
        "config/admin_cli.env.example must not contain FINTS_PRODUCT_VERSION"
    )


def test_db_init_does_not_call_update_product_registration_command() -> None:
    """db init must only run InitializeDatabaseCommand, never UpdateProductRegistrationCommand.

    Validates: Requirements 4.2
    """
    from gateway_admin.presentation.cli.db import _run_init

    mock_init_cmd_instance = AsyncMock()
    mock_init_cmd = MagicMock(return_value=mock_init_cmd_instance)
    mock_init_cmd.from_factory = MagicMock(return_value=mock_init_cmd_instance)

    mock_update_cmd_instance = AsyncMock()
    mock_update_cmd = MagicMock(return_value=mock_update_cmd_instance)
    mock_update_cmd.from_factory = MagicMock(return_value=mock_update_cmd_instance)

    mock_repo_factory = MagicMock()

    @asynccontextmanager
    async def mock_build_context():
        ctx = MagicMock()
        ctx.repo_factory = mock_repo_factory
        yield ctx

    with (
        patch(
            "gateway_admin.presentation.cli.db.InitializeDatabaseCommand",
            mock_init_cmd,
        ),
        patch(
            "gateway_admin.presentation.cli.db.UpdateProductRegistrationCommand",
            mock_update_cmd,
        ),
        patch(
            "gateway_admin.presentation.cli.db.build_context",
            mock_build_context,
        ),
    ):
        asyncio.run(_run_init())

    mock_init_cmd.from_factory.assert_called_once_with(mock_repo_factory)
    mock_init_cmd_instance.assert_awaited_once()
    mock_update_cmd.from_factory.assert_not_called()
    mock_update_cmd_instance.assert_not_awaited()
