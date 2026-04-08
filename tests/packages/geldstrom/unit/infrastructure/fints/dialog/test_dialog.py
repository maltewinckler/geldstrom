"""Tests for the FinTS dialog infrastructure modules.

These tests verify the Dialog class works correctly
without depending on the legacy FinTS3PinTanClient.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from geldstrom.infrastructure.fints.dialog import (
    DIALOG_ID_UNASSIGNED,
    SYSTEM_ID_UNASSIGNED,
    ConnectionConfig,
    Dialog,
    DialogConfig,
    DialogSnapshot,
    DialogState,
    HTTPSDialogConnection,
    ProcessedResponse,
    ResponseProcessor,
)
from geldstrom.infrastructure.fints.dialog.logging import mask_credentials
from geldstrom.infrastructure.fints.protocol import (
    BankIdentifier,
    Language2,
    ParameterStore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_connection():
    """Create a mock HTTP connection."""
    conn = MagicMock(spec=HTTPSDialogConnection)
    conn.url = "https://test.bank/fints"
    return conn


@pytest.fixture
def dialog_config():
    """Create a basic dialog configuration."""
    bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")

    return DialogConfig(
        bank_identifier=bank_id,
        user_id="testuser",
        customer_id="testuser",
        system_id=SYSTEM_ID_UNASSIGNED,
        product_name="TestProduct",
        product_version="1.0",
        language=Language2.DE,
    )


@pytest.fixture
def parameter_store():
    """Create an empty parameter store."""
    return ParameterStore()


@pytest.fixture
def mock_response():
    """Create a mock ProcessedResponse."""
    return ProcessedResponse(
        dialog_id="test-dialog-123",
        message_number=1,
        global_responses=[],
        segment_responses=[],
        bpd_version=78,
        upd_version=5,
    )


# ---------------------------------------------------------------------------
# DialogState Tests
# ---------------------------------------------------------------------------


class TestDialogState:
    """Tests for DialogState dataclass."""

    def test_default_values(self):
        """DialogState should have sensible defaults."""
        state = DialogState()
        assert state.dialog_id == DIALOG_ID_UNASSIGNED
        assert state.message_number == 1
        assert state.is_open is False
        assert state.is_initialized is False

    def test_custom_values(self):
        """DialogState should accept custom values."""
        state = DialogState(
            dialog_id="custom-123",
            message_number=5,
            is_open=True,
            is_initialized=True,
        )
        assert state.dialog_id == "custom-123"
        assert state.message_number == 5
        assert state.is_open is True


# ---------------------------------------------------------------------------
# DialogConfig Tests
# ---------------------------------------------------------------------------


class TestDialogConfig:
    """Tests for DialogConfig dataclass."""

    def test_minimal_config(self):
        """DialogConfig should require only essential fields."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        config = DialogConfig(
            bank_identifier=bank_id,
            user_id="user",
            customer_id="customer",
        )
        assert config.user_id == "user"
        assert config.system_id == SYSTEM_ID_UNASSIGNED
        assert config.language == Language2.DE

    def test_full_config(self, dialog_config):
        """DialogConfig should accept all fields."""
        assert dialog_config.user_id == "testuser"
        assert dialog_config.product_name == "TestProduct"
        assert dialog_config.product_version == "1.0"


# ---------------------------------------------------------------------------
# Dialog Tests
# ---------------------------------------------------------------------------


class TestDialog:
    """Tests for Dialog class."""

    def test_dialog_creation(self, mock_connection, dialog_config, parameter_store):
        """Dialog should initialize with correct state."""
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )

        assert dialog.dialog_id == DIALOG_ID_UNASSIGNED
        assert dialog.is_open is False
        assert dialog.parameters is parameter_store

    def test_dialog_cannot_send_when_closed(
        self, mock_connection, dialog_config, parameter_store
    ):
        """Dialog.send() should raise if not open."""
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )

        with pytest.raises(Exception, match="not open"):
            dialog.send(MagicMock())

    def test_dialog_cannot_init_twice(
        self, mock_connection, dialog_config, parameter_store, mock_response
    ):
        """Dialog.initialize() should raise if already open."""
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )

        # Mock the entire _send_segments to bypass message building
        with patch.object(dialog, "_send_segments") as mock_send:
            mock_send.return_value = mock_response

            # First init should work
            dialog.initialize()
            assert dialog.is_open

            # Second init should fail
            with pytest.raises(Exception, match="already open"):
                dialog.initialize()

    def test_dialog_end_when_not_open(
        self, mock_connection, dialog_config, parameter_store
    ):
        """Dialog.end() should be safe when not open."""
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )

        # Should not raise
        dialog.end()
        assert not dialog.is_open


# ---------------------------------------------------------------------------
# ConnectionConfig Tests
# ---------------------------------------------------------------------------


class TestConnectionConfig:
    """Tests for ConnectionConfig dataclass."""

    def test_minimal_config(self):
        """ConnectionConfig should require only URL."""
        config = ConnectionConfig(url="https://bank.example/fints")
        assert config.url == "https://bank.example/fints"
        assert config.timeout == 30.0

    def test_custom_timeout(self):
        """ConnectionConfig should accept custom timeout."""
        config = ConnectionConfig(url="https://bank.example/fints", timeout=60.0)
        assert config.timeout == 60.0


# ---------------------------------------------------------------------------
# HTTPSDialogConnection Tests
# ---------------------------------------------------------------------------


class TestHTTPSDialogConnection:
    """Tests for HTTPSDialogConnection class."""

    def test_creation_from_string(self):
        """HTTPSDialogConnection should accept URL string."""
        with patch("requests.Session"):
            conn = HTTPSDialogConnection("https://test.bank/fints")
            assert conn.url == "https://test.bank/fints"

    def test_creation_from_config(self):
        """HTTPSDialogConnection should accept ConnectionConfig."""
        config = ConnectionConfig(url="https://test.bank/fints", timeout=45.0)
        with patch("requests.Session"):
            conn = HTTPSDialogConnection(config)
            assert conn.url == "https://test.bank/fints"


# ---------------------------------------------------------------------------
# ResponseProcessor Tests
# ---------------------------------------------------------------------------


class TestResponseProcessor:
    """Tests for ResponseProcessor class."""

    def test_callback_registration(self):
        """ResponseProcessor should manage callbacks."""
        processor = ResponseProcessor()

        callback = MagicMock()
        processor.add_callback(callback)
        assert callback in processor._callbacks

        processor.remove_callback(callback)
        assert callback not in processor._callbacks


# ---------------------------------------------------------------------------
# Credential Masking Tests
# ---------------------------------------------------------------------------


class TestMaskCredentials:
    """Tests for credential masking in log output."""

    def test_masks_pin_single_quotes(self):
        """Should mask pin='value' format."""
        text = "UserDefinedSignature(pin='mysecretpin', tan=None)"
        result = mask_credentials(text)
        assert "mysecretpin" not in result
        assert "pin='***'" in result

    def test_masks_pin_double_quotes(self):
        """Should mask pin=\"value\" format."""
        text = 'UserDefinedSignature(pin="supersecret123", tan=None)'
        result = mask_credentials(text)
        assert "supersecret123" not in result
        assert "pin='***'" in result

    def test_masks_tan_single_quotes(self):
        """Should mask tan='value' format."""
        text = "UserDefinedSignature(pin='***', tan='123456')"
        result = mask_credentials(text)
        assert "123456" not in result
        assert "tan='***'" in result

    def test_masks_tan_double_quotes(self):
        """Should mask tan=\"value\" format."""
        text = 'UserDefinedSignature(pin="***", tan="mytan")'
        result = mask_credentials(text)
        assert "mytan" not in result
        assert "tan='***'" in result

    def test_masks_both_pin_and_tan(self):
        """Should mask both PIN and TAN together."""
        text = "UserDefinedSignature(pin='secret123', tan='tan456')"
        result = mask_credentials(text)
        assert "secret123" not in result
        assert "tan456" not in result
        assert "***" in result


# ---------------------------------------------------------------------------
# DialogSnapshot Tests
# ---------------------------------------------------------------------------


class TestDialogSnapshot:
    """Tests for DialogSnapshot serialization round-trip."""

    def test_to_dict_and_from_dict_round_trip(self):
        snapshot = DialogSnapshot(
            dialog_id="dlg-42",
            message_number=7,
            country_identifier="280",
            bank_code="12345678",
            user_id="testuser",
            customer_id="testuser",
            system_id="sys-abc",
            product_name="TestProduct",
            product_version="1.0",
            security_function="946",
        )
        restored = DialogSnapshot.from_dict(snapshot.to_dict())
        assert restored == snapshot

    def test_from_dict_coerces_message_number(self):
        data = {
            "dialog_id": "dlg-1",
            "message_number": "3",  # string, not int
            "country_identifier": "280",
            "bank_code": "87654321",
            "user_id": "u",
            "customer_id": "c",
            "system_id": "s",
            "product_name": "p",
            "product_version": "v",
            "security_function": "999",
        }
        snapshot = DialogSnapshot.from_dict(data)
        assert snapshot.message_number == 3
        assert isinstance(snapshot.message_number, int)

    def test_frozen(self):
        snapshot = DialogSnapshot(
            dialog_id="d",
            message_number=1,
            country_identifier="280",
            bank_code="12345678",
            user_id="u",
            customer_id="c",
            system_id="s",
            product_name="p",
            product_version="v",
            security_function="999",
        )
        with pytest.raises(Exception):
            snapshot.dialog_id = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Dialog.snapshot / Dialog.resume Tests
# ---------------------------------------------------------------------------


class TestDialogSnapshotResume:
    """Tests for Dialog.snapshot() and Dialog.resume()."""

    def test_snapshot_captures_state(
        self, mock_connection, dialog_config, parameter_store
    ):
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )
        dialog._state.dialog_id = "dlg-99"
        dialog._state.message_number = 5
        dialog._state.is_open = True

        snap = dialog.snapshot()

        assert snap.dialog_id == "dlg-99"
        assert snap.message_number == 5
        assert snap.user_id == "testuser"
        assert snap.security_function == "999"  # NoTanStrategy default

    def test_resume_creates_open_dialog(self, mock_connection, parameter_store):
        snap = DialogSnapshot(
            dialog_id="dlg-42",
            message_number=7,
            country_identifier="280",
            bank_code="12345678",
            user_id="testuser",
            customer_id="testuser",
            system_id="sys-abc",
            product_name="TestProduct",
            product_version="1.0",
            security_function="946",
        )
        dialog = Dialog.resume(
            snapshot=snap,
            connection=mock_connection,
            parameters=parameter_store,
        )

        assert dialog.is_open is True
        assert dialog.dialog_id == "dlg-42"
        assert dialog._state.message_number == 7
        assert dialog._state.is_initialized is True
        assert dialog.security_function == "946"

    def test_snapshot_resume_round_trip(
        self, mock_connection, dialog_config, parameter_store
    ):
        """snapshot() → resume() preserves dialog identity."""
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )
        dialog._state.dialog_id = "dlg-77"
        dialog._state.message_number = 3
        dialog._state.is_open = True

        snap = dialog.snapshot()

        new_conn = MagicMock(spec=HTTPSDialogConnection)
        resumed = Dialog.resume(
            snapshot=snap,
            connection=new_conn,
            parameters=parameter_store,
        )

        assert resumed.dialog_id == dialog.dialog_id
        assert resumed._state.message_number == dialog._state.message_number

    def test_preserves_non_sensitive_content(self):
        """Should not modify non-sensitive content."""
        text = "HKSAL:5:6+123456789::280:12345678+EUR"
        result = mask_credentials(text)
        assert "HKSAL" in result
        assert "123456789" in result
        assert "12345678" in result

    def test_case_insensitive(self):
        """Should mask regardless of case."""
        text = "PIN='secret' TAN='mytan'"
        result = mask_credentials(text)
        assert "secret" not in result
        assert "mytan" not in result

    def test_empty_string(self):
        """Should handle empty string."""
        assert mask_credentials("") == ""

    def test_no_credentials(self):
        """Should return unchanged text when no credentials present."""
        text = "Just some regular log message with numbers 12345"
        assert mask_credentials(text) == text


# ---------------------------------------------------------------------------
# TAN Strategy Tests
# ---------------------------------------------------------------------------


class TestTanStrategies:
    """Tests for TAN strategy classes."""

    def test_no_tan_strategy_properties(self):
        from geldstrom.infrastructure.fints.dialog.tan_strategies import NoTanStrategy

        strategy = NoTanStrategy()
        assert strategy.is_two_step is False
        assert strategy.security_function == "999"

    def test_decoupled_strategy_properties(self):
        from geldstrom.infrastructure.fints.dialog.tan_strategies import (
            DecoupledTanStrategy,
        )

        strategy = DecoupledTanStrategy("946")
        assert strategy.is_two_step is True
        assert strategy.security_function == "946"

    def test_dialog_uses_explicit_tan_strategy(
        self, mock_connection, dialog_config, parameter_store
    ):
        """Dialog should use explicitly provided tan_strategy."""
        from geldstrom.infrastructure.fints.dialog.tan_strategies import (
            DecoupledTanStrategy,
        )

        strategy = DecoupledTanStrategy("946")
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
            tan_strategy=strategy,
        )
        assert dialog.tan_strategy is strategy
        assert dialog.is_two_step_tan is True
        assert dialog.security_function == "946"

    def test_dialog_defaults_to_no_tan(
        self, mock_connection, dialog_config, parameter_store
    ):
        """Dialog without tan_strategy should default to NoTanStrategy."""
        dialog = Dialog(
            connection=mock_connection,
            config=dialog_config,
            parameters=parameter_store,
        )
        assert dialog.is_two_step_tan is False
        assert dialog.security_function == "999"
