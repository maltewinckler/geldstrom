"""FinTS 3.0 client implementation."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from datetime import date

from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    BankCredentials,
    BankRoute,
    SessionToken,
    TANConfig,
    TransactionFeed,
)
from geldstrom.domain.connection import ChallengeHandler, InteractiveChallengeHandler
from geldstrom.domain.model.tan import TANMethod
from geldstrom.infrastructure.fints import GatewayCredentials
from geldstrom.infrastructure.fints.adapters import (
    FinTSAccountDiscovery,
    FinTSBalanceAdapter,
    FinTSSessionAdapter,
    FinTSTANMethodsAdapter,
    FinTSTransactionHistory,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .base import BankClient


class FinTS3Client(BankClient):
    """FinTS 3.0 client for German online banking."""

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
        tan_config: TANConfig | None = None,
    ) -> None:
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
        self._init_common(session_state, challenge_handler, tan_config)

    @classmethod
    def from_gateway_credentials(
        cls,
        credentials: GatewayCredentials,
        *,
        session_state: SessionToken | None = None,
        challenge_handler: ChallengeHandler | None = None,
        tan_config: TANConfig | None = None,
    ) -> FinTS3Client:
        instance = cls.__new__(cls)
        instance._credentials = credentials
        instance._init_common(session_state, challenge_handler, tan_config)
        return instance

    def _init_common(
        self,
        session_state: SessionToken | None,
        challenge_handler: ChallengeHandler | None,
        tan_config: TANConfig | None,
    ) -> None:
        self._session_state: FinTSSessionState | None = (
            session_state if isinstance(session_state, FinTSSessionState) else None
        )
        self._challenge_handler = challenge_handler or InteractiveChallengeHandler()
        self._tan_config = tan_config or TANConfig()

        self._session_adapter: FinTSSessionAdapter | None = None
        self._account_adapter: FinTSAccountDiscovery | None = None
        self._balance_adapter: FinTSBalanceAdapter | None = None
        self._transaction_adapter: FinTSTransactionHistory | None = None
        self._tan_methods_adapter: FinTSTANMethodsAdapter | None = None
        self._accounts: Sequence[Account] = ()
        self._capabilities: BankCapabilities | None = None
        self._connected = False

        # Most German banks require a TAN method even for read operations.
        if not self._credentials.credentials.two_factor_method:
            warnings.warn(
                "No 'tan_method' configured. Most German banks require TAN "
                "authentication (2FA) even for basic operations like listing "
                "accounts. If you encounter errors, set 'tan_method' to your "
                "bank's TAN method (e.g., '946' for SecureGo+/Decoupled TAN).",
                UserWarning,
                stacklevel=3,
            )

    def __enter__(self) -> FinTS3Client:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def connect(self) -> Sequence[Account]:
        session_adapter = self._get_session_adapter()
        account_adapter = self._get_account_adapter()

        self._session_state = session_adapter.open_session(
            self._credentials,
            self._session_state,
        )
        self._capabilities = account_adapter.fetch_bank_capabilities(
            self._session_state
        )
        self._accounts = account_adapter.fetch_accounts(self._session_state)
        self._connected = True

        return self._accounts

    def disconnect(self) -> None:
        if self._session_state and self._session_adapter:
            self._session_adapter.close_session(self._session_state)
        self._connected = False
        self._accounts = ()
        self._capabilities = None

    def ensure_connected(self) -> None:
        if not self._connected:
            self.connect()

    def list_accounts(self) -> Sequence[Account]:
        self.ensure_connected()
        return self._accounts

    def get_account(self, account_id: str) -> Account:
        self.ensure_connected()
        for account in self._accounts:
            if account.account_id == account_id:
                return account
        raise ValueError(f"Account {account_id} not found")

    def get_balance(self, account: Account | str) -> BalanceSnapshot:
        if isinstance(account, str):
            account = self.get_account(account)

        self.ensure_connected()
        adapter = self._get_balance_adapter()
        return adapter.fetch_balance(self._session_state, account)

    def get_balances(
        self,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        self.ensure_connected()
        adapter = self._get_balance_adapter()
        return adapter.fetch_balances(self._session_state, account_ids)

    def get_transactions(
        self,
        account: Account | str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ) -> TransactionFeed:
        if isinstance(account, str):
            account_id = account
        else:
            account_id = account.account_id

        self.ensure_connected()
        adapter = self._get_transaction_adapter()
        return adapter.fetch_history(
            self._session_state,
            account_id,
            start_date,
            end_date,
            include_pending=include_pending,
        )

    def get_tan_methods(self) -> Sequence[TANMethod]:
        """Return TAN methods from BPD; performs a sync dialog if not yet connected."""
        adapter = self._get_tan_methods_adapter()
        return adapter.get_tan_methods(self._session_state)

    @property
    def session_state(self) -> SessionToken | None:
        """Current session state, can be persisted to resume without re-authentication."""
        return self._session_state

    @property
    def capabilities(self) -> BankCapabilities | None:
        return self._capabilities

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tan_config(self) -> TANConfig:
        return self._tan_config

    @tan_config.setter
    def tan_config(self, config: TANConfig) -> None:
        self._tan_config = config

    def _get_session_adapter(self) -> FinTSSessionAdapter:
        if self._session_adapter is None:
            self._session_adapter = FinTSSessionAdapter(
                tan_config=self._tan_config,
                challenge_handler=self._challenge_handler,
            )
        return self._session_adapter

    def _get_account_adapter(self) -> FinTSAccountDiscovery:
        if self._account_adapter is None:
            self._account_adapter = FinTSAccountDiscovery(
                self._credentials,
                tan_config=self._tan_config,
                challenge_handler=self._challenge_handler,
            )
        return self._account_adapter

    def _get_balance_adapter(self) -> FinTSBalanceAdapter:
        if self._balance_adapter is None:
            self._balance_adapter = FinTSBalanceAdapter(
                self._credentials,
                tan_config=self._tan_config,
                challenge_handler=self._challenge_handler,
            )
        return self._balance_adapter

    def _get_transaction_adapter(self) -> FinTSTransactionHistory:
        if self._transaction_adapter is None:
            self._transaction_adapter = FinTSTransactionHistory(
                self._credentials,
                tan_config=self._tan_config,
                challenge_handler=self._challenge_handler,
            )
        return self._transaction_adapter

    def _get_tan_methods_adapter(self) -> FinTSTANMethodsAdapter:
        if self._tan_methods_adapter is None:
            self._tan_methods_adapter = FinTSTANMethodsAdapter(
                self._credentials,
                tan_config=self._tan_config,
                challenge_handler=self._challenge_handler,
            )
        return self._tan_methods_adapter


__all__ = ["FinTS3Client"]
