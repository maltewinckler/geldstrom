"""Unit tests for FinTS3ClientDecoupled.

Tests focus on the decoupled-specific behavior: raising DecoupledTANPending,
pending state tracking, poll_tan delegation, and cleanup.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from geldstrom.clients.fints3_decoupled import (
    FinTS3ClientDecoupled,
    PollResult,
    _PendingTANState,
)
from geldstrom.domain.connection.challenge import DetachingChallengeHandler


class TestDecoupledClientInit:
    """Initialization and configuration tests."""

    def test_uses_detaching_handler_by_default(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        assert isinstance(client._challenge_handler, DetachingChallengeHandler)

    def test_from_gateway_credentials_returns_decoupled_type(self) -> None:
        from geldstrom.domain import BankCredentials, BankRoute
        from geldstrom.infrastructure.fints import GatewayCredentials

        creds = GatewayCredentials(
            route=BankRoute(country_code="DE", bank_code="87654321"),
            server_url="https://bank.example.com/fints",
            credentials=BankCredentials(user_id="user", secret="pass"),
            product_id="PROD123",
            product_version="1.0",
        )
        client = FinTS3ClientDecoupled.from_gateway_credentials(creds)
        assert isinstance(client, FinTS3ClientDecoupled)
        assert isinstance(client._challenge_handler, DetachingChallengeHandler)

    def test_has_no_pending_tan_initially(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        assert client.has_pending_tan is False
        assert client.pending_challenge is None


class TestPendingStateManagement:
    """Tests for pending TAN state tracking via poll_tan and cleanup."""

    def test_poll_tan_raises_when_no_pending(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        with pytest.raises(RuntimeError, match="No pending TAN"):
            client.poll_tan()

    def test_poll_tan_returns_pending_when_dialog_returns_none(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_dialog = MagicMock()
        mock_dialog.poll_decoupled_once.return_value = None
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=MagicMock(),
            operation_type="transactions",
            operation_meta={},
        )

        result = client.poll_tan()

        assert result.status == "pending"
        assert result.data is None
        assert client.has_pending_tan is True

    def test_poll_tan_returns_failed_on_timeout(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_dialog = MagicMock()
        mock_dialog.poll_decoupled_once.side_effect = TimeoutError("expired")
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=MagicMock(),
            operation_type="transactions",
            operation_meta={},
        )

        result = client.poll_tan()

        assert result.status == "failed"
        assert "expired" in (result.error or "")
        assert client.has_pending_tan is False

    def test_cleanup_clears_pending_state(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_dialog = MagicMock()
        mock_dialog.is_open = True
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = MagicMock()

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=MagicMock(),
            operation_type="transactions",
            operation_meta={},
        )

        client.cleanup_pending()

        assert client.has_pending_tan is False
        mock_dialog.end.assert_called_once()
        mock_ctx.connection.close.assert_called_once()

    def test_cleanup_is_idempotent(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        # No pending state — should not raise
        client.cleanup_pending()
        client.cleanup_pending()


class TestPollResult:
    """Tests for PollResult dataclass."""

    def test_pending_result(self) -> None:
        r = PollResult(status="pending")
        assert r.status == "pending"
        assert r.data is None
        assert r.error is None

    def test_approved_result_with_data(self) -> None:
        r = PollResult(status="approved", data={"key": "value"})
        assert r.data == {"key": "value"}

    def test_failed_result_with_error(self) -> None:
        r = PollResult(status="failed", error="something broke")
        assert r.error == "something broke"
