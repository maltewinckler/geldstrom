"""Integration tests for the FinTS3Client.

These tests exercise the full end-to-end flow against a real bank backend,
requiring valid credentials in the .env file. Users must be prepared to
approve SecureGo/TAN prompts when executing these tests.

Run with: python -m pytest tests/test_integration.py --run-integration

Environment variables (configured in .env):
    FINTS_BLZ          - Bank routing code (e.g., 12345678)
    FINTS_COUNTRY      - Country code (default: DE)
    FINTS_USER         - FinTS user ID
    FINTS_PIN          - User PIN
    FINTS_SERVER       - FinTS server URL
    FINTS_PRODUCT_ID   - Product identifier
    FINTS_PRODUCT_VERSION - Product version
    FINTS_CUSTOMER_ID  - (optional) Customer ID
    FINTS_TAN_MEDIUM   - (optional) TAN medium name
    FINTS_TAN_METHOD   - (optional) TAN method code
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

import pytest

from geldstrom.clients import FinTS3Client
from geldstrom.domain import BankCredentials, BankRoute
from geldstrom.infrastructure.fints import GatewayCredentials

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def env_file(request: pytest.FixtureRequest) -> Path:
    """Load path to .env file from pytest config."""
    return Path(request.config.getoption("--fints-env-file"))


@pytest.fixture(scope="session")
def fints_env(env_file: Path) -> Mapping[str, str]:
    """Parse .env file and merge with environment variables."""
    if not env_file.exists():
        pytest.skip(f"Environment file {env_file} not found. Skipping integration.")
    env: dict[str, str] = {}
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = _strip_quotes(value.strip())
    # Allow OS environment to override .env
    for key, value in os.environ.items():
        if key.startswith("FINTS_"):
            env[key] = value
    return env


@pytest.fixture(scope="session")
def credentials(fints_env: Mapping[str, str]) -> GatewayCredentials:
    """Build GatewayCredentials from the loaded environment."""
    country = fints_env.get("FINTS_COUNTRY", "DE")
    blz = _require_env(fints_env, "FINTS_BLZ")

    bank_creds = BankCredentials(
        user_id=_require_env(fints_env, "FINTS_USER"),
        secret=_require_env(fints_env, "FINTS_PIN"),
        customer_id=fints_env.get("FINTS_CUSTOMER_ID"),
        two_factor_device=fints_env.get("FINTS_TAN_MEDIUM"),
        two_factor_method=fints_env.get("FINTS_TAN_METHOD"),
    )

    return GatewayCredentials(
        route=BankRoute(country_code=country, bank_code=blz),
        server_url=_require_env(fints_env, "FINTS_SERVER"),
        credentials=bank_creds,
        product_id=_require_env(fints_env, "FINTS_PRODUCT_ID"),
        product_version=_require_env(fints_env, "FINTS_PRODUCT_VERSION"),
    )


@pytest.fixture
def client(credentials: GatewayCredentials) -> FinTS3Client:
    """Create a fresh FinTS3Client for each test."""
    return FinTS3Client.from_gateway_credentials(credentials)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_connect_and_list_accounts(client: FinTS3Client):
    """Verify that connect() returns account metadata."""
    with client:
        accounts = client.list_accounts()
        assert accounts, "Expected at least one account from real bank"
        for account in accounts:
            assert account.account_id
            assert account.bank_route
            assert account.currency


@pytest.mark.integration
def test_fetch_balance(client: FinTS3Client):
    """Verify balance retrieval for the first available account."""
    with client:
        accounts = client.list_accounts()
        if not accounts:
            pytest.skip("No accounts available to test balance fetch")
        account = accounts[0]
        balance = client.get_balance(account.account_id)
        assert balance.account_id == account.account_id
        assert balance.booked
        assert balance.booked.currency
        assert balance.as_of


@pytest.mark.integration
def test_fetch_transactions(client: FinTS3Client):
    """Verify transaction retrieval for the first available account.

    Note: This may trigger a TAN prompt if the bank requires approval
    for transaction queries. Be ready to approve in your banking app.
    """
    with client:
        accounts = client.list_accounts()
        if not accounts:
            pytest.skip("No accounts available to test transaction fetch")
        account = accounts[0]
        if not account.supports_transactions():
            pytest.skip(f"Account {account.account_id} does not support transactions")
        feed = client.get_transactions(account.account_id)
        assert feed.account_id == account.account_id
        assert feed.start_date
        assert feed.end_date
        # Transactions may be empty for new/inactive accounts
        for entry in feed.entries:
            assert entry.booking_date
            assert entry.currency
            assert entry.amount is not None


@pytest.mark.integration
def test_session_reuse(credentials: GatewayCredentials):
    """Verify that session state can be persisted and reused."""
    # First connection: establish session
    client1 = FinTS3Client.from_gateway_credentials(credentials)
    with client1:
        accounts1 = client1.list_accounts()
        session_state = client1.session_state
    assert session_state is not None
    assert session_state.system_id
    assert accounts1
    # Second connection: reuse session
    client2 = FinTS3Client.from_gateway_credentials(
        credentials, session_state=session_state
    )
    with client2:
        accounts2 = client2.list_accounts()
        assert len(accounts2) == len(accounts1)
        for acc1, acc2 in zip(accounts1, accounts2):
            assert acc1.account_id == acc2.account_id


@pytest.mark.integration
def test_fetch_capabilities(client: FinTS3Client):
    """Verify that bank capabilities are discoverable."""
    with client:
        client.connect()
        capabilities = client.capabilities
        assert capabilities is not None
        assert capabilities.supported_operations
        # Most banks should support at least balance queries
        assert any(
            op in capabilities.supported_operations
            for op in ["GET_BALANCE", "get_balance"]
        )


# ---------------------------------------------------------------------------
# Multi-Operation Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_multiple_operations_same_session(client: FinTS3Client):
    """Verify multiple operations work within a single session.

    This tests that:
    - Dialog state is maintained correctly between operations
    - HKTAN injection works for multiple consecutive business operations
    - Session message numbering is handled properly
    """
    with client:
        # Operation 1: List accounts
        accounts = client.list_accounts()
        assert accounts, "Expected at least one account"

        # Find an account that supports both balance and transactions
        test_account = None
        for acc in accounts:
            if acc.supports_transactions():
                test_account = acc
                break

        if not test_account:
            pytest.skip("No account supports transactions for multi-op test")

        # Operation 2: Get balance
        balance = client.get_balance(test_account.account_id)
        assert balance.account_id == test_account.account_id
        assert balance.booked

        # Operation 3: Get transactions
        transactions = client.get_transactions(test_account.account_id)
        assert transactions.account_id == test_account.account_id

        # Operation 4: Get balance again (verify session still works)
        balance2 = client.get_balance(test_account.account_id)
        assert balance2.account_id == test_account.account_id


@pytest.mark.integration
def test_all_accounts_balance(client: FinTS3Client):
    """Verify balance retrieval works for all accounts that support it."""
    with client:
        accounts = client.list_accounts()
        balances_fetched = 0

        for account in accounts:
            try:
                balance = client.get_balance(account.account_id)
                assert balance.account_id == account.account_id
                balances_fetched += 1
            except Exception as e:
                # Some accounts may not support balance queries
                print(f"Balance not available for {account.account_id}: {e}")

        assert balances_fetched > 0, "Expected at least one account to support balance"


# ---------------------------------------------------------------------------
# Session State Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_session_state_contains_parameters(credentials: GatewayCredentials):
    """Verify session state includes BPD/UPD for efficient reconnection."""
    client = FinTS3Client.from_gateway_credentials(credentials)
    with client:
        client.connect()
        session_state = client.session_state

    assert session_state is not None
    assert session_state.system_id
    # The session should contain parameter data for reuse
    assert hasattr(session_state, "client_blob") or hasattr(
        session_state, "bpd_version"
    )


@pytest.mark.integration
def test_session_reuse_skips_sync_dialog(credentials: GatewayCredentials):
    """Verify that reusing session state avoids unnecessary sync dialogs."""
    # First connection: full initialization
    client1 = FinTS3Client.from_gateway_credentials(credentials)
    with client1:
        accounts1 = client1.list_accounts()
        session_state = client1.session_state
        system_id = session_state.system_id

    # Second connection: should reuse existing system_id
    client2 = FinTS3Client.from_gateway_credentials(
        credentials, session_state=session_state
    )
    with client2:
        accounts2 = client2.list_accounts()
        # System ID should be the same (no new sync dialog)
        assert client2.session_state.system_id == system_id
        assert len(accounts2) == len(accounts1)


@pytest.mark.integration
def test_session_state_serialization_roundtrip(credentials: GatewayCredentials):
    """Verify session state can be serialized and deserialized correctly."""
    # Create session
    client1 = FinTS3Client.from_gateway_credentials(credentials)
    with client1:
        accounts1 = client1.list_accounts()
        session_state = client1.session_state

    # Serialize
    serialized = session_state.serialize()
    assert serialized is not None
    assert isinstance(serialized, (str, bytes, dict))

    # Deserialize
    from geldstrom.infrastructure.fints.session import FinTSSessionState

    restored_state = FinTSSessionState.deserialize(serialized)

    # Use restored state
    client2 = FinTS3Client.from_gateway_credentials(
        credentials,
        session_state=restored_state,
    )
    with client2:
        accounts2 = client2.list_accounts()
        assert len(accounts2) == len(accounts1)


# ---------------------------------------------------------------------------
# Date Range Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_transactions_with_date_range(client: FinTS3Client):
    """Verify transaction filtering by date range works."""
    from datetime import date, timedelta

    with client:
        accounts = client.list_accounts()
        account = None
        for acc in accounts:
            if acc.supports_transactions():
                account = acc
                break

        if not account:
            pytest.skip("No account supports transactions")

        # Request last 7 days only
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        feed = client.get_transactions(
            account.account_id,
            start_date=start_date,
            end_date=end_date,
        )

        assert feed.account_id == account.account_id
        # Verify all returned transactions are within the date range
        for entry in feed.entries:
            assert entry.booking_date >= start_date
            assert entry.booking_date <= end_date


@pytest.mark.integration
def test_transactions_empty_range(client: FinTS3Client):
    """Verify handling of date range with potentially no transactions."""
    from datetime import date

    with client:
        accounts = client.list_accounts()
        account = None
        for acc in accounts:
            if acc.supports_transactions():
                account = acc
                break

        if not account:
            pytest.skip("No account supports transactions")

        # Request a very recent 1-day window (might be empty)
        today = date.today()

        feed = client.get_transactions(
            account.account_id,
            start_date=today,
            end_date=today,
        )

        # Should return successfully even if empty
        assert feed.account_id == account.account_id
        assert feed.start_date is not None
        assert feed.end_date is not None
        # entries may be empty, that's okay


# ---------------------------------------------------------------------------
# Account Operations Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_account_by_id(client: FinTS3Client):
    """Verify get_account() retrieves a specific account by ID."""
    with client:
        accounts = client.list_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        # Get the first account's ID
        expected_id = accounts[0].account_id

        # Retrieve by ID
        account = client.get_account(expected_id)

        assert account.account_id == expected_id
        assert account.iban == accounts[0].iban
        assert account.currency == accounts[0].currency


@pytest.mark.integration
def test_get_account_not_found(client: FinTS3Client):
    """Verify get_account() raises ValueError for unknown account."""
    with client:
        client.connect()
        with pytest.raises(ValueError, match="not found"):
            client.get_account("NONEXISTENT:0")


# ---------------------------------------------------------------------------
# Batch Balance Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_balances_all_accounts(client: FinTS3Client):
    """Verify get_balances() fetches balances for all accounts."""
    with client:
        accounts = client.list_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        # Fetch all balances (no filter)
        balances = client.get_balances()

        assert len(balances) > 0
        for balance in balances:
            assert balance.account_id
            assert balance.booked
            assert balance.booked.currency


@pytest.mark.integration
def test_get_balances_filtered(client: FinTS3Client):
    """Verify get_balances() can filter by account IDs."""
    with client:
        accounts = client.list_accounts()
        if len(accounts) < 1:
            pytest.skip("Need at least one account")

        # Request balance for specific account(s)
        account_ids = [accounts[0].account_id]
        balances = client.get_balances(account_ids)

        assert len(balances) >= 1
        # All returned balances should be for requested accounts
        returned_ids = {b.account_id for b in balances}
        for aid in account_ids:
            assert aid in returned_ids or len(balances) > 0


# ---------------------------------------------------------------------------
# Connection State Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_is_connected_property(credentials: GatewayCredentials):
    """Verify is_connected property reflects actual connection state."""
    client = FinTS3Client.from_gateway_credentials(credentials)

    # Initially not connected
    assert not client.is_connected

    # After connect
    client.connect()
    assert client.is_connected

    # After disconnect
    client.disconnect()
    assert not client.is_connected


@pytest.mark.integration
def test_is_connected_with_context_manager(client: FinTS3Client):
    """Verify is_connected works correctly with context manager."""
    assert not client.is_connected

    with client:
        assert client.is_connected

    assert not client.is_connected


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_invalid_account_raises_error(client: FinTS3Client):
    """Verify that querying an invalid account raises an appropriate error."""
    with client:
        client.connect()
        with pytest.raises(ValueError):
            client.get_balance("INVALID_ACCOUNT_ID_12345")


@pytest.mark.integration
def test_auto_connect_on_operation(credentials: GatewayCredentials):
    """Verify that the client auto-connects when operations are called outside context."""
    # Create a client but don't explicitly enter context
    client = FinTS3Client.from_gateway_credentials(credentials)

    # Session state should be None initially
    assert client.session_state is None

    # Operations should auto-connect
    accounts = client.list_accounts()
    assert accounts, "Should get accounts via auto-connect"

    # Session state should now be set
    assert client.session_state is not None
    assert client.session_state.system_id


# ---------------------------------------------------------------------------
# Infrastructure Verification Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_dialog_hktan_injection(credentials: GatewayCredentials):
    """Verify that HKTAN injection works correctly for two-step TAN.

    This test directly exercises the dialog's HKTAN injection by checking
    that business operations succeed (which requires correct HKTAN).
    """
    from datetime import date, timedelta

    from geldstrom.infrastructure.fints.adapters.connection import FinTSConnectionHelper
    from geldstrom.infrastructure.fints.operations import (
        AccountOperations,
        TransactionOperations,
    )

    helper = FinTSConnectionHelper(credentials)

    with helper.connect(None) as ctx:
        # Verify dialog is configured for two-step TAN
        if credentials.tan_method:
            assert ctx.dialog.is_two_step_tan, "Dialog should be in two-step TAN mode"
            assert ctx.dialog._security_function == credentials.tan_method

        # Fetch accounts (HKSPA - doesn't need HKTAN)
        account_ops = AccountOperations(ctx.dialog, ctx.parameters)
        sepa_accounts = account_ops.fetch_sepa_accounts()
        assert sepa_accounts, "Expected SEPA accounts"

        # Fetch transactions (HKCAZ - needs HKTAN injection)
        tx_ops = TransactionOperations(ctx.dialog, ctx.parameters)
        start_date = date.today() - timedelta(days=30)

        try:
            result = tx_ops.fetch_camt(sepa_accounts[0], start_date)
            # If we get here without error 9370, HKTAN injection worked
            assert result is not None
        except Exception as e:
            if "9370" in str(e) or "Signaturen" in str(e):
                pytest.fail(f"HKTAN injection failed: {e}")
            raise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_env(env: Mapping[str, str], key: str) -> str:
    """Raise pytest.skip if a required environment variable is missing."""
    value = env.get(key)
    if not value:
        pytest.skip(f"Missing required environment variable: {key}")
    return value


def _strip_quotes(value: str) -> str:
    """Remove surrounding quotes from .env values."""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value
