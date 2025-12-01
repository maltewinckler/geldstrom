"""Modern FinTS 3.0 client using domain-driven architecture.

This client provides a clean, type-safe interface for FinTS banking operations.
It uses domain port adapters internally, following DDD principles.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from geldstrom.application.ports import GatewayCredentials
from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    BankCredentials,
    BankRoute,
    SessionToken,
    StatementDocument,
    StatementReference,
    TransactionFeed,
)
from geldstrom.domain.connection import ChallengeHandler, InteractiveChallengeHandler
from geldstrom.infrastructure.fints.adapters import (
    FinTSAccountDiscovery,
    FinTSBalanceAdapter,
    FinTSSessionAdapter,
    FinTSStatementAdapter,
    FinTSTransactionHistory,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .base import ClientCredentials


class FinTS3Client:
    """
    Modern FinTS 3.0 client with clean domain-driven architecture.

    This client provides access to FinTS banking operations using
    the new adapter-based infrastructure. It supports:

    - Account discovery and listing
    - Balance queries
    - Transaction history (MT940 and CAMT formats)
    - Statement retrieval
    - Decoupled TAN (app-based confirmation)

    Example:
        from geldstrom import FinTS3Client
        from geldstrom.domain import BankCredentials, BankRoute

        creds = ClientCredentials(
            route=BankRoute("DE", "12345678"),
            server_url="https://banking.example.com/fints",
            credentials=BankCredentials(
                user_id="user123",
                secret="mypin",
                two_factor_device="SecureGo",
            ),
            product_id="MYPRODUCT123",
        )

        with FinTS3Client(creds) as client:
            accounts = client.list_accounts()
            for acc in accounts:
                balance = client.get_balance(acc)
                print(f"{acc.iban}: {balance.booked.amount} {balance.booked.currency}")
    """

    def __init__(
        self,
        credentials: ClientCredentials | GatewayCredentials,
        *,
        session_state: SessionToken | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        """
        Initialize the FinTS 3.0 client.

        Args:
            credentials: Bank connection credentials
            session_state: Optional existing session state to resume
            challenge_handler: Optional handler for 2FA challenges
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

        self._session_state: FinTSSessionState | None = (
            session_state if isinstance(session_state, FinTSSessionState) else None
        )
        self._challenge_handler = challenge_handler or InteractiveChallengeHandler()

        # Adapters (created lazily to avoid import cycles)
        self._session_adapter: FinTSSessionAdapter | None = None
        self._account_adapter: FinTSAccountDiscovery | None = None
        self._balance_adapter: FinTSBalanceAdapter | None = None
        self._transaction_adapter: FinTSTransactionHistory | None = None
        self._statement_adapter: FinTSStatementAdapter | None = None

        # Cached data
        self._accounts: Sequence[Account] = ()
        self._capabilities: BankCapabilities | None = None
        self._connected = False

    # --- Context manager ---

    def __enter__(self) -> "FinTS3Client":
        """Enter context and connect to bank."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and close session."""
        self.disconnect()

    # --- Connection management ---

    def connect(self) -> Sequence[Account]:
        """
        Establish connection and fetch account metadata.

        Returns:
            Sequence of available accounts

        Raises:
            RuntimeError: If connection fails
        """
        session_adapter = self._get_session_adapter()
        account_adapter = self._get_account_adapter()

        # Open or resume session
        self._session_state = session_adapter.open_session(
            self._credentials,
            self._session_state,
        )

        # Fetch capabilities and accounts
        self._capabilities = account_adapter.fetch_bank_capabilities(
            self._session_state
        )
        self._accounts = account_adapter.fetch_accounts(self._session_state)
        self._connected = True

        return self._accounts

    def disconnect(self) -> None:
        """Close the session (if open)."""
        if self._session_state and self._session_adapter:
            self._session_adapter.close_session(self._session_state)
        self._connected = False

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

    def get_account(self, account_id: str) -> Account:
        """
        Get a specific account by ID.

        Args:
            account_id: Account identifier (format: "account_number:subaccount")

        Returns:
            Account object

        Raises:
            ValueError: If account not found
        """
        for account in self.list_accounts():
            if account.account_id == account_id:
                return account
        raise ValueError(f"Account {account_id} not found")

    # --- Balance operations ---

    def get_balance(self, account: Account | str) -> BalanceSnapshot:
        """
        Fetch current balance for an account.

        Args:
            account: Account object or account_id string

        Returns:
            BalanceSnapshot with current balance

        Raises:
            ValueError: If account not found
            RuntimeError: If not connected
        """
        if isinstance(account, str):
            account = self.get_account(account)

        state = self._require_session()
        adapter = self._get_balance_adapter()
        return adapter.fetch_balance(state, account)

    def get_balances(
        self,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        """
        Fetch balances for multiple accounts.

        Args:
            account_ids: Optional list of account IDs (default: all accounts)

        Returns:
            Sequence of BalanceSnapshot objects
        """
        state = self._require_session()
        adapter = self._get_balance_adapter()
        return adapter.fetch_balances(state, account_ids)

    # --- Transaction operations ---

    def get_transactions(
        self,
        account: Account | str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ) -> TransactionFeed:
        """
        Fetch transaction history for an account.

        Args:
            account: Account object or account_id string
            start_date: Optional start date filter
            end_date: Optional end date filter
            include_pending: Whether to include pending transactions

        Returns:
            TransactionFeed with transaction entries

        Raises:
            ValueError: If account not found
            RuntimeError: If not connected
        """
        if isinstance(account, str):
            account_id = account
        else:
            account_id = account.account_id

        state = self._require_session()
        adapter = self._get_transaction_adapter()
        return adapter.fetch_history(
            state,
            account_id,
            start_date,
            end_date,
            include_pending=include_pending,
        )

    # --- Statement operations ---

    def list_statements(self, account: Account | str) -> Sequence[StatementReference]:
        """
        List available statements for an account.

        Args:
            account: Account object or account_id string

        Returns:
            Sequence of StatementReference objects
        """
        if isinstance(account, str):
            account_id = account
        else:
            account_id = account.account_id

        state = self._require_session()
        adapter = self._get_statement_adapter()
        return adapter.list_statements(state, account_id)

    def get_statement(
        self,
        reference: StatementReference,
        *,
        preferred_format: str | None = None,
    ) -> StatementDocument:
        """
        Fetch a specific statement.

        Args:
            reference: Statement reference from list_statements()
            preferred_format: Preferred MIME type (e.g., "application/pdf")

        Returns:
            StatementDocument with content
        """
        state = self._require_session()
        adapter = self._get_statement_adapter()
        return adapter.fetch_statement(
            state,
            reference,
            preferred_mime_type=preferred_format,
        )

    # --- Properties ---

    @property
    def session_state(self) -> SessionToken | None:
        """
        Current session state for persistence.

        Save this to resume sessions without re-authenticating:
            state = client.session_state
            # ... later ...
            client = FinTS3Client(creds, session_state=state)
        """
        return self._session_state

    @property
    def capabilities(self) -> BankCapabilities | None:
        """Bank's advertised capabilities."""
        return self._capabilities

    @property
    def is_connected(self) -> bool:
        """Whether the client is currently connected."""
        return self._connected

    # --- Internal helpers ---

    def _require_session(self) -> FinTSSessionState:
        """Ensure we have an active session."""
        if not self._session_state:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._session_state

    def _get_session_adapter(self) -> FinTSSessionAdapter:
        """Lazy-create session adapter."""
        if self._session_adapter is None:
            self._session_adapter = FinTSSessionAdapter()
        return self._session_adapter

    def _get_account_adapter(self) -> FinTSAccountDiscovery:
        """Lazy-create account adapter."""
        if self._account_adapter is None:
            self._account_adapter = FinTSAccountDiscovery(self._credentials)
        return self._account_adapter

    def _get_balance_adapter(self) -> FinTSBalanceAdapter:
        """Lazy-create balance adapter."""
        if self._balance_adapter is None:
            self._balance_adapter = FinTSBalanceAdapter(
                self._credentials,
                self._accounts,
            )
        return self._balance_adapter

    def _get_transaction_adapter(self) -> FinTSTransactionHistory:
        """Lazy-create transaction adapter."""
        if self._transaction_adapter is None:
            self._transaction_adapter = FinTSTransactionHistory(self._credentials)
        return self._transaction_adapter

    def _get_statement_adapter(self) -> FinTSStatementAdapter:
        """Lazy-create statement adapter."""
        if self._statement_adapter is None:
            self._statement_adapter = FinTSStatementAdapter(self._credentials)
        return self._statement_adapter


__all__ = ["FinTS3Client"]

