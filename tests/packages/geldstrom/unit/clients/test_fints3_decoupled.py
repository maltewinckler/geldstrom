"""Unit tests for FinTS3ClientDecoupled.

Tests focus on the decoupled-specific behavior: raising DecoupledTANPending,
pending state tracking, poll_tan delegation, and cleanup.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from geldstrom.clients.fints3 import FinTS3Client
from geldstrom.clients.fints3_decoupled import (
    FinTS3ClientDecoupled,
    PollResult,
    _PendingTANState,
)
from geldstrom.infrastructure.fints.challenge import (
    DecoupledTANPending,
    DetachingChallengeHandler,
)


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
        from geldstrom.infrastructure.fints.credentials import GatewayCredentials

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

    def test_connect_pending_preserves_session_state(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_ctx = MagicMock()
        pending = DecoupledTANPending(MagicMock(), "task-ref", context=mock_ctx)
        expected_state = MagicMock()

        client._session_adapter = MagicMock()
        client._session_adapter.create_session_state.return_value = expected_state

        with patch.object(FinTS3Client, "connect", side_effect=pending):
            with pytest.raises(DecoupledTANPending):
                client.connect()

        assert client.session_state is expected_state

    def test_poll_tan_returns_accounts_after_connect_approval(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_dialog = MagicMock()
        mock_dialog.is_open = False
        mock_dialog.poll_decoupled_once.return_value = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=MagicMock(),
            operation_type="connect",
            operation_meta={"was_connected": False},
        )

        expected_accounts = (MagicMock(),)
        with patch.object(
            client,
            "_resume_accounts_from_context",
            return_value=expected_accounts,
        ) as resume_accounts:
            result = client.poll_tan()

        assert result.status == "approved"
        assert result.data == expected_accounts
        resume_accounts.assert_called_once_with(mock_ctx)
        assert client.has_pending_tan is False

    def test_poll_tan_resumes_balance_after_connect_approval(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_dialog = MagicMock()
        mock_dialog.is_open = False
        mock_dialog.poll_decoupled_once.return_value = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=MagicMock(),
            operation_type="balance",
            operation_meta={"account_id": "123456:0", "was_connected": False},
        )

        expected_balance = MagicMock()
        with patch.object(client, "_resume_accounts_from_context") as resume_accounts:
            with patch.object(
                client,
                "_fetch_balance_from_context",
                return_value=expected_balance,
            ) as fetch_balance:
                result = client.poll_tan()

        assert result.status == "approved"
        assert result.data is expected_balance
        resume_accounts.assert_called_once_with(mock_ctx)
        fetch_balance.assert_called_once_with(mock_ctx, "123456:0")
        assert client.has_pending_tan is False

    def test_poll_tan_returns_tan_methods_after_approval(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        mock_dialog = MagicMock()
        mock_dialog.is_open = False
        mock_dialog.poll_decoupled_once.return_value = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=MagicMock(),
            operation_type="tan_methods",
            operation_meta={"was_connected": False},
        )

        expected_methods = (MagicMock(),)
        with patch.object(
            client,
            "_extract_tan_methods_from_context",
            return_value=expected_methods,
        ) as extract_tan_methods:
            result = client.poll_tan()

        assert result.status == "approved"
        assert result.data == expected_methods
        extract_tan_methods.assert_called_once_with(mock_ctx)
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


class TestSnapshotPending:
    """Tests for FinTS3ClientDecoupled.snapshot_pending()."""

    def test_snapshot_raises_without_pending(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        with pytest.raises(RuntimeError, match="No pending TAN"):
            client.snapshot_pending()

    def test_snapshot_returns_serialized_bytes(self) -> None:
        from geldstrom.infrastructure.fints.session_snapshot import (
            DecoupledSessionSnapshot,
        )

        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        mock_dialog = MagicMock()
        mock_dialog.snapshot.return_value = MagicMock(
            to_dict=MagicMock(return_value={"dialog_id": "dlg-1", "message_number": 3})
        )
        mock_dialog.is_open = False

        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None
        mock_ctx.credentials.server_url = "https://bank.example.com/fints"

        mock_session_state = MagicMock()
        mock_session_state.serialize.return_value = b"\x01\x02"

        client._session_adapter = MagicMock()
        client._session_adapter.create_session_state.return_value = mock_session_state

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref-42",
            challenge=MagicMock(),
            operation_type="transactions",
            operation_meta={"account_id": "DE123"},
        )

        raw = client.snapshot_pending()

        # Should be deserializable
        snapshot = DecoupledSessionSnapshot.deserialize(raw)
        assert snapshot.task_reference == "task-ref-42"
        assert snapshot.operation_type == "transactions"
        assert snapshot.operation_meta == {"account_id": "DE123"}
        assert snapshot.server_url == "https://bank.example.com/fints"

        # Pending state should be cleared
        assert client.has_pending_tan is False

    def test_snapshot_cleans_up_connection(self) -> None:
        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        mock_dialog = MagicMock()
        mock_dialog.snapshot.return_value = MagicMock(
            to_dict=MagicMock(return_value={"dialog_id": "d"})
        )
        mock_dialog.is_open = True
        mock_connection = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = mock_connection
        mock_ctx.credentials.server_url = "https://x"

        mock_session_state = MagicMock()
        mock_session_state.serialize.return_value = b""

        client._session_adapter = MagicMock()
        client._session_adapter.create_session_state.return_value = mock_session_state

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="t",
            challenge=MagicMock(),
            operation_type="accounts",
            operation_meta={},
        )

        client.snapshot_pending()

        # dialog.end() must NOT be called — the dialog must stay open at the
        # bank so that subsequent HKTAN process=S poll messages are accepted.
        mock_dialog.end.assert_not_called()
        mock_connection.close.assert_called_once()


class TestApprovedOperationPagination:
    """Tests for the fix: TAN approval with partial data must not lose transactions."""

    def test_falls_through_to_pagination_when_3040_present(self) -> None:
        """When the TAN approval response has entries AND a 3040 continuation code,
        the client must NOT return the partial data early. Instead it must fall
        through to _fetch_transactions_from_context for full paginated fetch."""
        from datetime import date
        from unittest.mock import MagicMock, patch

        from geldstrom.clients.fints3_decoupled import (
            FinTS3ClientDecoupled,
            _PendingTANState,
        )
        from geldstrom.domain import TransactionEntry, TransactionFeed
        from geldstrom.infrastructure.fints.dialog.responses import DialogResponse

        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        # Build a mock response that has entries AND a 3040 "more data" code.
        mock_response = MagicMock()
        mock_response.get_response_by_code.side_effect = lambda code: (
            DialogResponse(
                code="3040", text="Weitere Einträge vorhanden", parameters=("ABC123",)
            )
            if code == "3040"
            else None
        )
        mock_response.raw_response = MagicMock()

        mock_dialog = MagicMock()
        mock_dialog.is_open = False
        mock_dialog.poll_decoupled_once.return_value = mock_response
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=None,
            operation_type="transactions",
            operation_meta={
                "account_id": "DE89370400440532013000:0",
                "start_date": "2025-05-01",
                "end_date": "2026-04-30",
                "was_connected": True,
            },
        )

        # Full feed that _fetch_transactions_from_context should return:
        # First page entries (from approval response):
        first_page_feed = TransactionFeed(
            account_id="DE89370400440532013000:0",
            entries=(
                TransactionEntry(
                    entry_id="1",
                    booking_date=date(2025, 6, 1),
                    value_date=date(2025, 6, 1),
                    amount=100,
                    currency="EUR",
                    purpose="Page 1 - from approval",
                ),
            ),
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
        )

        # Continuation entries (pages 2+):
        continuation_feed = TransactionFeed(
            account_id="DE89370400440532013000:0",
            entries=(
                TransactionEntry(
                    entry_id="2",
                    booking_date=date(2026, 3, 15),
                    value_date=date(2026, 3, 15),
                    amount=200,
                    currency="EUR",
                    purpose="Page 2 - would have been lost without fix",
                ),
            ),
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 15),
        )

        client._session_adapter = MagicMock()
        client._session_adapter.create_session_state.return_value = MagicMock()

        with patch(
            "geldstrom.clients.fints3_decoupled.parse_mt940_approved_response",
            return_value=first_page_feed,
        ):
            with patch(
                "geldstrom.clients.fints3_decoupled.parse_camt_approved_response",
                return_value=TransactionFeed(
                    account_id="DE89370400440532013000:0",
                    entries=(),
                    start_date=date(2025, 6, 1),
                    end_date=date(2025, 6, 1),
                ),
            ):
                with patch.object(
                    client,
                    "_fetch_continuation_from_context",
                    return_value=continuation_feed,
                ) as fetch_continuation:
                    result = client.poll_tan()

        assert result.status == "approved"
        assert len(result.data.entries) == 2
        assert result.data.entries[0].purpose == "Page 1 - from approval"
        assert (
            result.data.entries[1].purpose
            == "Page 2 - would have been lost without fix"
        )
        # Verify continuation was called with the touchdown point
        fetch_continuation.assert_called_once()
        call_args = fetch_continuation.call_args
        assert call_args[0][1] == "DE89370400440532013000:0"  # account_id
        assert call_args[0][2] == "ABC123"  # touchdown_point
        assert call_args[1].get("use_camt") is False  # MT940 had entries

    def test_uses_camt_continuation_when_mt940_has_no_entries(self) -> None:
        """When the bank returns CAMT data (not MT940) with a 3040 continuation,
        the client should pass use_camt=True to _fetch_continuation_from_context."""
        from datetime import date
        from unittest.mock import MagicMock, patch

        from geldstrom.clients.fints3_decoupled import (
            FinTS3ClientDecoupled,
            _PendingTANState,
        )
        from geldstrom.domain import TransactionEntry, TransactionFeed
        from geldstrom.infrastructure.fints.dialog.responses import DialogResponse

        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        mock_response = MagicMock()
        mock_response.get_response_by_code.side_effect = lambda code: (
            DialogResponse(
                code="3040", text="Weitere Einträge vorhanden", parameters=("CAMT_TD",)
            )
            if code == "3040"
            else None
        )
        mock_response.raw_response = MagicMock()

        mock_dialog = MagicMock()
        mock_dialog.is_open = False
        mock_dialog.poll_decoupled_once.return_value = mock_response
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=None,
            operation_type="transactions",
            operation_meta={
                "account_id": "DE89370400440532013000:0",
                "start_date": "2025-05-01",
                "end_date": "2026-04-30",
                "was_connected": True,
            },
        )

        # MT940 returns empty, CAMT returns first page
        empty_mt940 = TransactionFeed(
            account_id="DE89370400440532013000:0",
            entries=(),
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
        )
        camt_first_page = TransactionFeed(
            account_id="DE89370400440532013000:0",
            entries=(
                TransactionEntry(
                    entry_id="c1",
                    booking_date=date(2025, 6, 1),
                    value_date=date(2025, 6, 1),
                    amount=100,
                    currency="EUR",
                    purpose="CAMT page 1",
                ),
            ),
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
        )
        continuation_feed = TransactionFeed(
            account_id="DE89370400440532013000:0",
            entries=(
                TransactionEntry(
                    entry_id="c2",
                    booking_date=date(2026, 3, 15),
                    value_date=date(2026, 3, 15),
                    amount=200,
                    currency="EUR",
                    purpose="CAMT page 2",
                ),
            ),
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 15),
        )

        client._session_adapter = MagicMock()
        client._session_adapter.create_session_state.return_value = MagicMock()

        with patch(
            "geldstrom.clients.fints3_decoupled.parse_mt940_approved_response",
            return_value=empty_mt940,
        ):
            with patch(
                "geldstrom.clients.fints3_decoupled.parse_camt_approved_response",
                return_value=camt_first_page,
            ):
                with patch.object(
                    client,
                    "_fetch_continuation_from_context",
                    return_value=continuation_feed,
                ) as fetch_continuation:
                    result = client.poll_tan()

        assert result.status == "approved"
        assert len(result.data.entries) == 2
        assert result.data.entries[0].purpose == "CAMT page 1"
        assert result.data.entries[1].purpose == "CAMT page 2"
        fetch_continuation.assert_called_once()
        call_args = fetch_continuation.call_args
        assert call_args[0][2] == "CAMT_TD"
        assert call_args[1].get("use_camt") is True  # CAMT had entries, not MT940

    def test_returns_early_when_no_3040_and_entries_present(self) -> None:
        """When the TAN approval response has entries but NO 3040 (all data fits
        in one page), the client should return the parsed entries directly."""
        from datetime import date
        from unittest.mock import MagicMock, patch

        from geldstrom.clients.fints3_decoupled import (
            FinTS3ClientDecoupled,
            _PendingTANState,
        )
        from geldstrom.domain import TransactionEntry, TransactionFeed

        client = FinTS3ClientDecoupled(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        # Response with entries but NO 3040 code.
        mock_response = MagicMock()
        mock_response.get_response_by_code.return_value = None  # No 3040
        mock_response.raw_response = MagicMock()

        mock_dialog = MagicMock()
        mock_dialog.is_open = False
        mock_dialog.poll_decoupled_once.return_value = mock_response
        mock_ctx = MagicMock()
        mock_ctx.dialog = mock_dialog
        mock_ctx.connection = None

        client._pending = _PendingTANState(
            context=mock_ctx,
            task_reference="task-ref",
            challenge=None,
            operation_type="transactions",
            operation_meta={
                "account_id": "DE89370400440532013000:0",
                "start_date": "2025-05-01",
                "end_date": "2025-06-01",
                "was_connected": True,
            },
        )

        small_feed = TransactionFeed(
            account_id="DE89370400440532013000:0",
            entries=(
                TransactionEntry(
                    entry_id="1",
                    booking_date=date(2025, 5, 15),
                    value_date=date(2025, 5, 15),
                    amount=50,
                    currency="EUR",
                    purpose="Short range, single page",
                ),
            ),
            start_date=date(2025, 5, 15),
            end_date=date(2025, 5, 15),
        )

        client._session_adapter = MagicMock()
        client._session_adapter.create_session_state.return_value = MagicMock()

        with patch(
            "geldstrom.clients.fints3_decoupled.parse_mt940_approved_response",
            return_value=small_feed,
        ):
            with patch(
                "geldstrom.clients.fints3_decoupled.parse_camt_approved_response",
                return_value=TransactionFeed(
                    account_id="DE89370400440532013000:0",
                    entries=(),
                    start_date=date(2025, 5, 15),
                    end_date=date(2025, 5, 15),
                ),
            ):
                with patch.object(
                    client,
                    "_fetch_continuation_from_context",
                ) as fetch_continuation:
                    result = client.poll_tan()

        assert result.status == "approved"
        assert result.data is small_feed
        assert len(result.data.entries) == 1
        # Should NOT have called the continuation path
        fetch_continuation.assert_not_called()
