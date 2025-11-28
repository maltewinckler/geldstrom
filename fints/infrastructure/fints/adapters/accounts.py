"""FinTS 3.0 implementation of AccountDiscoveryPort."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Sequence

from fints.application.ports import GatewayCredentials
from fints.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankCapabilities,
    BankRoute,
)
from fints.domain.ports.accounts import AccountDiscoveryPort
from fints.infrastructure.fints import FinTSOperations
from fints.infrastructure.fints.session import FinTSSessionState
from fints.formals import BankIdentifier as FinTSBankIdentifier

if TYPE_CHECKING:
    from fints.client import FinTS3PinTanClient
    from fints.models import SEPAAccount


class FinTSAccountDiscovery(AccountDiscoveryPort):
    """
    FinTS 3.0 implementation of AccountDiscoveryPort.

    Discovers accounts and bank capabilities via FinTS dialogs.
    """

    def __init__(self, credentials: GatewayCredentials) -> None:
        """
        Initialize with credentials for building clients.

        Args:
            credentials: Bank connection credentials
        """
        self._credentials = credentials

    def fetch_bank_capabilities(
        self,
        state: FinTSSessionState,
    ) -> BankCapabilities:
        """
        Fetch bank capabilities from BPD.

        Args:
            state: Current session state

        Returns:
            BankCapabilities with supported operations
        """
        client = self._build_client(state)
        with self._logged_in(client):
            info = client.get_information()
        return self._capabilities_from_info(info)

    def fetch_accounts(
        self,
        state: FinTSSessionState,
    ) -> Sequence[Account]:
        """
        Fetch all accounts available to the user.

        Args:
            state: Current session state

        Returns:
            Sequence of Account domain objects
        """
        client = self._build_client(state)
        with self._logged_in(client):
            info = client.get_information()
            sepa_accounts = client.get_sepa_accounts()
        return self._accounts_from_info(
            self._credentials.route,
            info,
            sepa_accounts,
        )

    # --- Internal helpers ---

    def _build_client(
        self,
        state: FinTSSessionState,
    ) -> "FinTS3PinTanClient":
        """Build a configured FinTS client from session state."""
        from fints.client import FinTS3PinTanClient

        creds = self._credentials
        kwargs: dict[str, Any] = {
            "bank_identifier": creds.route.bank_code,
            "user_id": creds.user_id,
            "pin": creds.pin,
            "server": creds.server_url,
            "customer_id": creds.customer_id or creds.user_id,
            "product_id": creds.product_id,
            "product_version": creds.product_version,
            "tan_medium": creds.tan_medium,
            "from_data": state.client_blob,
            "system_id": state.system_id,
        }

        client = FinTS3PinTanClient(**kwargs)

        if creds.tan_method:
            client.set_tan_mechanism(creds.tan_method)

        return client

    @contextmanager
    def _logged_in(self, client: "FinTS3PinTanClient"):
        """Context manager for client login/logout."""
        with client:
            yield client

    def _capabilities_from_info(self, info: dict) -> BankCapabilities:
        """Extract bank capabilities from get_information response."""
        supported = {
            op.name
            for op, enabled in info.get("bank", {})
            .get("supported_operations", {})
            .items()
            if enabled
        }
        formats = {
            op.name: tuple(fmt_list)
            for op, fmt_list in info.get("bank", {})
            .get("supported_formats", {})
            .items()
        }
        return BankCapabilities(
            supported_operations=frozenset(supported),
            supported_formats=formats,
        )

    def _accounts_from_info(
        self,
        default_route: BankRoute,
        info: dict,
        sepa_accounts: Sequence["SEPAAccount"],
    ) -> Sequence[Account]:
        """Convert FinTS account info to domain Account objects."""
        sepa_lookup = {self._account_key(sepa): sepa for sepa in sepa_accounts}
        domain_accounts: list[Account] = []

        for acc in info.get("accounts", []):
            account_number = acc.get("account_number")
            sub_number = acc.get("subaccount_number") or "0"
            account_id = f"{account_number}:{sub_number}"
            sepa = sepa_lookup.get(account_id)

            bank_identifier = acc.get("bank_identifier")
            route = (
                self._route_from_identifier(bank_identifier)
                if bank_identifier
                else default_route
            )

            owner_names = acc.get("owner_name", [])
            owner = AccountOwner(name=owner_names[0]) if owner_names else None

            capabilities = self._account_capabilities(
                acc.get("supported_operations", {})
            )

            # Build metadata with string coercion for non-string values
            acc_type = acc.get("type")
            metadata_raw = {
                "account_number": account_number,
                "subaccount_number": sub_number,
                "customer_id": acc.get("customer_id"),
                "type": str(acc_type) if acc_type is not None else None,
            }

            domain_accounts.append(
                Account(
                    account_id=account_id,
                    iban=acc.get("iban"),
                    bic=sepa.bic if sepa else None,
                    currency=acc.get("currency"),
                    product_name=acc.get("product_name"),
                    owner=owner,
                    bank_route=route,
                    capabilities=capabilities,
                    raw_labels=tuple(owner_names),
                    metadata={k: v for k, v in metadata_raw.items() if v is not None},
                )
            )

        return tuple(domain_accounts)

    def _account_capabilities(self, ops: dict) -> AccountCapabilities:
        """Convert FinTS operation flags to AccountCapabilities."""
        return AccountCapabilities(
            can_fetch_balance=self._is_enabled(ops, FinTSOperations.GET_BALANCE),
            can_list_transactions=self._supports_any(
                ops,
                FinTSOperations.GET_TRANSACTIONS,
                FinTSOperations.GET_TRANSACTIONS_XML,
            ),
            can_fetch_statements=self._supports_any(
                ops,
                FinTSOperations.GET_STATEMENT,
                FinTSOperations.GET_STATEMENT_PDF,
            ),
            can_fetch_holdings=self._is_enabled(ops, FinTSOperations.GET_HOLDINGS),
            can_fetch_scheduled_debits=self._supports_any(
                ops,
                FinTSOperations.GET_SCHEDULED_DEBITS_SINGLE,
                FinTSOperations.GET_SCHEDULED_DEBITS_MULTIPLE,
            ),
        )

    @staticmethod
    def _is_enabled(ops: dict, operation: FinTSOperations) -> bool:
        """Check if an operation is enabled."""
        value = ops.get(operation)
        if isinstance(value, bool):
            return value
        return bool(value)

    def _supports_any(self, ops: dict, *operations: FinTSOperations) -> bool:
        """Check if any of the operations is enabled."""
        return any(self._is_enabled(ops, op) for op in operations)

    @staticmethod
    def _account_key(account: "SEPAAccount") -> str:
        """Create lookup key from SEPA account."""
        return f"{account.accountnumber}:{account.subaccount or '0'}"

    @staticmethod
    def _route_from_identifier(identifier) -> BankRoute:
        """Convert FinTS BankIdentifier to domain BankRoute."""
        country_numeric = identifier.country_identifier
        country_code = FinTSBankIdentifier.COUNTRY_NUMERIC_TO_ALPHA.get(
            country_numeric,
            country_numeric,
        )
        return BankRoute(country_code=country_code, bank_code=identifier.bank_code)


__all__ = ["FinTSAccountDiscovery"]

