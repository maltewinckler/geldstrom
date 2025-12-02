"""Unit tests for FinTS3Client.

These tests mock the underlying adapters to test the client's public API
in isolation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from geldstrom.clients import FinTS3Client
from geldstrom.clients.base import BankClient
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceAmount,
    BalanceSnapshot,
    BankCapabilities,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.infrastructure.fints import GatewayCredentials
from geldstrom.infrastructure.fints.session import FinTSSessionState


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session_state() -> FinTSSessionState:
    """Create a mock session state."""
    state = MagicMock(spec=FinTSSessionState)
    return state


@pytest.fixture
def sample_account() -> Account:
    """Create a sample account for testing."""
    return Account(
        account_id="123456:0",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        currency="EUR",
        owner=AccountOwner(name="Test User"),
        bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        capabilities=AccountCapabilities(
            can_fetch_balance=True,
            can_list_transactions=True,
            can_fetch_statements=False,
            can_fetch_holdings=False,
        ),
    )


@pytest.fixture
def sample_balance() -> BalanceSnapshot:
    """Create a sample balance snapshot."""
    from datetime import datetime

    return BalanceSnapshot(
        account_id="123456:0",
        booked=BalanceAmount(amount=Decimal("1234.56"), currency="EUR"),
        available=None,
        as_of=datetime(2025, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def sample_feed() -> TransactionFeed:
    """Create a sample transaction feed."""
    return TransactionFeed(
        account_id="123456:0",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        entries=[
            TransactionEntry(
                entry_id="TX001",
                amount=Decimal("100.00"),
                currency="EUR",
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                purpose="Test transaction",
                counterpart_name="Test Merchant",
            ),
        ],
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestClientInitialization:
    """Tests for FinTS3Client initialization."""

    def test_init_with_required_params(self):
        """Client can be initialized with required parameters."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        assert client._credentials.route.bank_code == "12345678"
        assert client._credentials.server_url == "https://example.com/fints"
        assert client._credentials.user_id == "testuser"
        assert client._credentials.product_id == "TESTPROD"
        assert not client.is_connected

    def test_init_with_optional_params(self):
        """Client accepts all optional parameters."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
            country_code="AT",
            customer_id="customer123",
            tan_medium="SecureGo",
            tan_method="921",
            product_version="2.0",
        )

        assert client._credentials.route.country_code == "AT"
        assert client._credentials.credentials.customer_id == "customer123"
        assert client._credentials.credentials.two_factor_device == "SecureGo"
        assert client._credentials.credentials.two_factor_method == "921"
        assert client._credentials.product_version == "2.0"

    def test_from_gateway_credentials(self):
        """Client can be created from GatewayCredentials."""
        from geldstrom.domain import BankCredentials, BankRoute

        creds = GatewayCredentials(
            route=BankRoute(country_code="DE", bank_code="87654321"),
            server_url="https://bank.example.com/fints",
            credentials=BankCredentials(user_id="user", secret="pass"),
            product_id="PROD123",
            product_version="1.0",
        )

        client = FinTS3Client.from_gateway_credentials(creds)

        assert client._credentials is creds
        assert not client.is_connected

    def test_implements_bank_client_protocol(self):
        """FinTS3Client inherits from BankClient."""
        # FinTS3Client explicitly inherits from BankClient
        assert BankClient in FinTS3Client.__mro__


# =============================================================================
# Connection Tests
# =============================================================================


class TestConnectionManagement:
    """Tests for connection lifecycle."""

    @patch("geldstrom.clients.fints3.FinTSSessionAdapter")
    @patch("geldstrom.clients.fints3.FinTSAccountDiscovery")
    def test_connect_returns_accounts(
        self,
        mock_discovery_cls,
        mock_session_cls,
        sample_account,
        mock_session_state,
    ):
        """connect() establishes session and returns accounts."""
        # Setup mocks
        mock_session = MagicMock()
        mock_session.open_session.return_value = mock_session_state
        mock_session_cls.return_value = mock_session

        mock_discovery = MagicMock()
        mock_discovery.fetch_bank_capabilities.return_value = BankCapabilities()
        mock_discovery.fetch_accounts.return_value = [sample_account]
        mock_discovery_cls.return_value = mock_discovery

        # Test
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        accounts = client.connect()

        assert len(accounts) == 1
        assert accounts[0].account_id == "123456:0"
        assert client.is_connected
        mock_session.open_session.assert_called_once()
        mock_discovery.fetch_accounts.assert_called_once()

    @patch("geldstrom.clients.fints3.FinTSSessionAdapter")
    def test_disconnect_closes_session(self, mock_session_cls, mock_session_state):
        """disconnect() closes the session."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._session_state = mock_session_state
        client._session_adapter = mock_session
        client._connected = True

        client.disconnect()

        assert not client.is_connected
        mock_session.close_session.assert_called_once_with(mock_session_state)

    @patch("geldstrom.clients.fints3.FinTSSessionAdapter")
    @patch("geldstrom.clients.fints3.FinTSAccountDiscovery")
    def test_context_manager(
        self,
        mock_discovery_cls,
        mock_session_cls,
        sample_account,
        mock_session_state,
    ):
        """Client works as context manager."""
        mock_session = MagicMock()
        mock_session.open_session.return_value = mock_session_state
        mock_session_cls.return_value = mock_session

        mock_discovery = MagicMock()
        mock_discovery.fetch_bank_capabilities.return_value = BankCapabilities()
        mock_discovery.fetch_accounts.return_value = [sample_account]
        mock_discovery_cls.return_value = mock_discovery

        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        with client as c:
            assert c.is_connected
            assert len(c.list_accounts()) == 1

        assert not client.is_connected
        mock_session.close_session.assert_called_once()


# =============================================================================
# Account Operations Tests
# =============================================================================


class TestAccountOperations:
    """Tests for account-related operations."""

    def test_list_accounts_returns_cached(self, sample_account):
        """list_accounts() returns cached accounts if available."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._accounts = [sample_account]

        accounts = client.list_accounts()

        assert len(accounts) == 1
        assert accounts[0].account_id == "123456:0"

    def test_get_account_by_id(self, sample_account):
        """get_account() returns account by ID."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._accounts = [sample_account]

        account = client.get_account("123456:0")

        assert account.iban == "DE89370400440532013000"

    def test_get_account_not_found(self, sample_account):
        """get_account() raises ValueError if account not found."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._accounts = [sample_account]

        with pytest.raises(ValueError, match="not found"):
            client.get_account("999999:0")


# =============================================================================
# Balance Operations Tests
# =============================================================================


class TestBalanceOperations:
    """Tests for balance operations."""

    @patch("geldstrom.clients.fints3.FinTSBalanceAdapter")
    def test_get_balance_with_account_object(
        self,
        mock_adapter_cls,
        sample_account,
        sample_balance,
        mock_session_state,
    ):
        """get_balance() works with Account object."""
        mock_adapter = MagicMock()
        mock_adapter.fetch_balance.return_value = sample_balance
        mock_adapter_cls.return_value = mock_adapter

        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._session_state = mock_session_state
        client._accounts = [sample_account]

        balance = client.get_balance(sample_account)

        assert balance.booked.amount == Decimal("1234.56")
        mock_adapter.fetch_balance.assert_called_once_with(
            mock_session_state, sample_account
        )

    @patch("geldstrom.clients.fints3.FinTSBalanceAdapter")
    def test_get_balance_with_account_id(
        self,
        mock_adapter_cls,
        sample_account,
        sample_balance,
        mock_session_state,
    ):
        """get_balance() works with account_id string."""
        mock_adapter = MagicMock()
        mock_adapter.fetch_balance.return_value = sample_balance
        mock_adapter_cls.return_value = mock_adapter

        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._session_state = mock_session_state
        client._accounts = [sample_account]

        balance = client.get_balance("123456:0")

        assert balance.booked.amount == Decimal("1234.56")

    def test_get_balance_not_connected(self, sample_account):
        """get_balance() raises RuntimeError if not connected."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._accounts = [sample_account]

        with pytest.raises(RuntimeError, match="Not connected"):
            client.get_balance(sample_account)


# =============================================================================
# Transaction Operations Tests
# =============================================================================


class TestTransactionOperations:
    """Tests for transaction operations."""

    @patch("geldstrom.clients.fints3.FinTSTransactionHistory")
    def test_get_transactions_with_dates(
        self,
        mock_adapter_cls,
        sample_account,
        sample_feed,
        mock_session_state,
    ):
        """get_transactions() passes date filters to adapter."""
        mock_adapter = MagicMock()
        mock_adapter.fetch_history.return_value = sample_feed
        mock_adapter_cls.return_value = mock_adapter

        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._session_state = mock_session_state
        client._accounts = [sample_account]

        start = date(2025, 1, 1)
        end = date(2025, 1, 31)
        feed = client.get_transactions(sample_account, start_date=start, end_date=end)

        assert len(feed.entries) == 1
        mock_adapter.fetch_history.assert_called_once_with(
            mock_session_state,
            "123456:0",
            start,
            end,
            include_pending=False,
        )

    @patch("geldstrom.clients.fints3.FinTSTransactionHistory")
    def test_get_transactions_with_account_id(
        self,
        mock_adapter_cls,
        sample_feed,
        mock_session_state,
    ):
        """get_transactions() works with account_id string."""
        mock_adapter = MagicMock()
        mock_adapter.fetch_history.return_value = sample_feed
        mock_adapter_cls.return_value = mock_adapter

        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._session_state = mock_session_state

        feed = client.get_transactions("123456:0")

        assert feed.account_id == "123456:0"
        mock_adapter.fetch_history.assert_called_once()


# =============================================================================
# Properties Tests
# =============================================================================


class TestProperties:
    """Tests for client properties."""

    def test_session_state_property(self, mock_session_state):
        """session_state property returns current state."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        client._session_state = mock_session_state

        assert client.session_state is mock_session_state

    def test_capabilities_property(self):
        """capabilities property returns bank capabilities."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )
        caps = BankCapabilities()
        client._capabilities = caps

        assert client.capabilities is caps

    def test_is_connected_property(self):
        """is_connected property reflects connection state."""
        client = FinTS3Client(
            bank_code="12345678",
            server_url="https://example.com/fints",
            user_id="testuser",
            pin="testpin",
            product_id="TESTPROD",
        )

        assert not client.is_connected

        client._connected = True
        assert client.is_connected

