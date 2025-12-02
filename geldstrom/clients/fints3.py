"""Modern FinTS 3.0 client with a simple, user-friendly API.

This client provides a clean interface for FinTS banking operations.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

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
from geldstrom.infrastructure.fints import GatewayCredentials
from geldstrom.infrastructure.fints.adapters import (
    FinTSAccountDiscovery,
    FinTSBalanceAdapter,
    FinTSSessionAdapter,
    FinTSStatementAdapter,
    FinTSTransactionHistory,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .base import BankClient


class FinTS3Client(BankClient):
    """
    FinTS 3.0 client for German online banking.

    Provides access to:
    - Account discovery and listing
    - Balance queries
    - Transaction history (MT940 and CAMT formats)
    - Statement retrieval
    - Decoupled TAN (app-based 2FA)

    Example:
        from geldstrom import FinTS3Client

        with FinTS3Client(
            bank_code="12345678",
            server_url="https://banking.example.com/fints",
            user_id="user123",
            pin="mypin",
            product_id="MYPRODUCT123",
        ) as client:
            for account in client.list_accounts():
                balance = client.get_balance(account)
                print(f"{account.iban}: {balance.booked.amount}")
    """

    def __init__(
        self,
        bank_code: str,
        server_url: str,
        user_id: str,
        pin: str,
        product_id: str,
        *,
        country_code: str = "DE",
        customer_id: str | None = None,
        tan_medium: str | None = None,
        tan_method: str | None = None,
        product_version: str = "1.0",
        session_state: SessionToken | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        """
        Initialize the FinTS 3.0 client.

        Args:
            bank_code: Bank identifier (BLZ in Germany, e.g., "12345678")
            server_url: FinTS server URL (e.g., "https://banking.example.com/fints")
            user_id: Your online banking username
            pin: Your online banking PIN
            product_id: FinTS product registration ID

        Keyword Args:
            country_code: Country code (default: "DE" for Germany)
            customer_id: Customer ID if different from user_id (rare)
            tan_medium: TAN device name (e.g., "SecureGo" for push TAN)
            tan_method: TAN method identifier (usually auto-detected)
            product_version: Product version string (default: "1.0")
            session_state: Existing session state to resume
            challenge_handler: Custom handler for 2FA challenges
        """
        self._credentials = GatewayCredentials(
            route=BankRoute(country_code=country_code, bank_code=bank_code),
            server_url=server_url,
            credentials=BankCredentials(
                user_id=user_id,
                secret=pin,
                customer_id=customer_id,
                two_factor_device=tan_medium,
                two_factor_method=tan_method,
            ),
            product_id=product_id,
            product_version=product_version,
        )
        self._init_common(session_state, challenge_handler)

    @classmethod
    def from_gateway_credentials(
        cls,
        credentials: GatewayCredentials,
        *,
        session_state: SessionToken | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> FinTS3Client:
        """
        Create client from pre-built GatewayCredentials.

        This is useful for advanced scenarios or when credentials
        are constructed programmatically.

        Args:
            credentials: Pre-built GatewayCredentials object
            session_state: Optional existing session state to resume
            challenge_handler: Optional handler for 2FA challenges

        Returns:
            Configured FinTS3Client instance
        """
        instance = cls.__new__(cls)
        instance._credentials = credentials
        instance._init_common(session_state, challenge_handler)
        return instance

    def _init_common(
        self,
        session_state: SessionToken | None,
        challenge_handler: ChallengeHandler | None,
    ) -> None:
        """Common initialization logic."""
        self._session_state: FinTSSessionState | None = (
            session_state if isinstance(session_state, FinTSSessionState) else None
        )
        self._challenge_handler = challenge_handler or InteractiveChallengeHandler()

        # Adapters (created lazily)
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

    def __enter__(self) -> FinTS3Client:
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
            client = FinTS3Client.from_gateway_credentials(creds, session_state=state)
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
            self._balance_adapter = FinTSBalanceAdapter(self._credentials)
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
