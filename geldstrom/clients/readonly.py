"""Read-only FinTS client using the gateway-based architecture.

This client provides a simpler interface for read-only operations,
using the application layer services and BankGateway protocol.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from geldstrom.application import (
    AccountDiscoveryService,
    BalanceService,
    BankGateway,
    GatewayCredentials,
    TransactionHistoryService,
)
from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    SessionToken,
    TransactionFeed,
)
from geldstrom.infrastructure import FinTSReadOnlyGateway

from .base import ClientCredentials


class ReadOnlyFinTSClient:
    """
    High-level read-only client for FinTS banking operations.

    This client provides a simple interface for:
    - Account discovery and listing
    - Balance queries
    - Transaction history

    It uses the application layer services with a pluggable gateway,
    making it suitable for testing with mock implementations.

    Example:
        from geldstrom import ReadOnlyFinTSClient
        from geldstrom.application import GatewayCredentials
        from geldstrom.domain import BankCredentials, BankRoute

        creds = GatewayCredentials(
            route=BankRoute("DE", "12345678"),
            server_url="https://banking.example.com/fints",
            credentials=BankCredentials(
                user_id="user123",
                secret="mypin",
            ),
            product_id="MYPRODUCT123",
            product_version="1.0",
        )

        with ReadOnlyFinTSClient(creds) as client:
            for account in client.list_accounts():
                balance = client.get_balance(account.account_id)
                print(f"{account.iban}: {balance.booked.amount}")
    """

    def __init__(
        self,
        credentials: GatewayCredentials | ClientCredentials,
        session_state: SessionToken | None = None,
        gateway: BankGateway | None = None,
    ) -> None:
        """
        Initialize the read-only client.

        Args:
            credentials: Bank connection credentials
            session_state: Optional existing session state to resume
            gateway: Optional gateway implementation (default: FinTSReadOnlyGateway)
        """
        # Convert ClientCredentials to GatewayCredentials if needed
        if isinstance(credentials, ClientCredentials):
            self._credentials = GatewayCredentials(
                route=credentials.route,
                server_url=credentials.server_url,
                credentials=credentials.credentials,
                product_id=credentials.product_id,
                product_version=credentials.product_version,
            )
        else:
            self._credentials = credentials

        self._session_state = session_state
        self._gateway = gateway or FinTSReadOnlyGateway()

        # Application services
        self._discovery = AccountDiscoveryService(self._gateway)
        self._balances = BalanceService(self._gateway)
        self._transactions = TransactionHistoryService(self._gateway)

        # Cached data
        self._accounts: Sequence[Account] = ()
        self._capabilities: BankCapabilities | None = None

    # --- Context manager ---

    def __enter__(self) -> ReadOnlyFinTSClient:
        """Enter context and connect."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Exit context (no cleanup needed for read-only)."""

    # --- Connection ---
    def connect(
        self,
        session_state: SessionToken | None = None,
    ) -> Sequence[Account]:
        """
        Connect to the bank and fetch account metadata.

        Args:
            session_state: Optional session state to use

        Returns:
            Sequence of available accounts
        """
        state_hint = session_state or self._session_state
        state, capabilities, accounts = self._discovery.execute(
            self._credentials,
            session=state_hint,
        )
        self._session_state = state
        self._capabilities = capabilities
        self._accounts = tuple(accounts)
        return self._accounts

    # --- Account operations ---

    def list_accounts(self) -> Sequence[Account]:
        """
        Return available accounts.

        Automatically connects if not already connected.

        Returns:
            Sequence of Account objects
        """
        if not self._accounts:
            return self.connect()
        return self._accounts

    # --- Balance operations ---

    def get_balance(self, account_id: str) -> BalanceSnapshot:
        """
        Fetch current balance for an account.

        Args:
            account_id: Account identifier

        Returns:
            BalanceSnapshot with current balance

        Raises:
            ValueError: If account not found
            RuntimeError: If not connected
        """
        account = self._require_account(account_id)
        state = self._require_session()
        return self._balances.fetch(self._credentials, state, account)

    # --- Transaction operations ---

    def get_transactions(
        self,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed:
        """
        Fetch transaction history for an account.

        Args:
            account_id: Account identifier
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            TransactionFeed with transaction entries

        Raises:
            ValueError: If account not found
            RuntimeError: If not connected
        """
        account = self._require_account(account_id)
        state = self._require_session()
        return self._transactions.fetch(
            self._credentials,
            state,
            account,
            start_date,
            end_date,
        )

    # --- Properties ---

    @property
    def session_state(self) -> SessionToken | None:
        """Current session state for persistence."""
        return self._session_state

    @property
    def capabilities(self) -> BankCapabilities | None:
        """Bank's advertised capabilities."""
        return self._capabilities

    # --- Internal helpers ---

    def _require_session(self) -> SessionToken:
        """Ensure we have an active session."""
        if not self._session_state:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._session_state

    def _require_account(self, account_id: str) -> Account:
        """Find account by ID or raise ValueError."""
        for account in self.list_accounts():
            if account.account_id == account_id:
                return account
        raise ValueError(f"Account {account_id} not known. Call connect() to refresh.")


__all__ = ["ReadOnlyFinTSClient"]
