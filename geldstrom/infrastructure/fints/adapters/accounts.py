"""FinTS 3.0 implementation of AccountDiscoveryPort."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

from geldstrom.application.ports import GatewayCredentials
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankCapabilities,
    BankRoute,
)
from geldstrom.domain.ports.accounts import AccountDiscoveryPort
from geldstrom.infrastructure.fints.protocol import BankIdentifier as FinTSBankIdentifier
from geldstrom.infrastructure.fints.session import FinTSSessionState
from geldstrom.infrastructure.fints.operations import AccountInfo

from .connection import FinTSConnectionHelper

if TYPE_CHECKING:
    from geldstrom.models import SEPAAccount

logger = logging.getLogger(__name__)


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
        helper = FinTSConnectionHelper(self._credentials)

        with helper.connect(state) as ctx:
            # Get supported operations from BPD
            supported_ops = ctx.parameters.bpd.get_supported_operations()

            # Convert to domain format
            supported = {name for name, enabled in supported_ops.items() if enabled}
            return BankCapabilities(
                supported_operations=frozenset(supported),
                supported_formats={},  # TODO: Extract from BPD
            )

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
        from geldstrom.infrastructure.fints.operations import AccountOperations

        helper = FinTSConnectionHelper(self._credentials)

        with helper.connect(state) as ctx:
            ops = AccountOperations(ctx.dialog, ctx.parameters)

            # Fetch SEPA accounts and UPD accounts
            sepa_accounts = ops.fetch_sepa_accounts()
            upd_accounts = list(ops.get_accounts_from_upd())
            if not upd_accounts and sepa_accounts:
                logger.warning(
                    "UPD accounts missing; synthesizing from %d SEPA accounts",
                    len(sepa_accounts),
                )
                for sepa in sepa_accounts:
                    upd_accounts.append(
                        AccountInfo(
                            account_number=sepa.accountnumber or sepa.iban,
                            subaccount_number=sepa.subaccount,
                            iban=sepa.iban,
                            bic=sepa.bic,
                            currency="EUR",
                            owner_name=[],
                            product_name=None,
                            account_type=None,
                            bank_identifier=None,
                            allowed_operations=[],
                        )
                    )
            logger.warning(
                "Fetched %d SEPA accounts, %d UPD accounts",
                len(sepa_accounts),
                len(upd_accounts),
            )

            # Merge and convert to domain
            return self._accounts_from_operations(
                self._credentials.route,
                upd_accounts,
                sepa_accounts,
            )

    # --- Helpers ---

    def _accounts_from_operations(
        self,
        default_route: BankRoute,
        upd_accounts,
        sepa_accounts: Sequence["SEPAAccount"],
    ) -> Sequence[Account]:
        """Convert operations result to domain Account objects."""

        sepa_lookup = {self._account_key(sepa): sepa for sepa in sepa_accounts}
        domain_accounts: list[Account] = []

        for acc in upd_accounts:
            if not isinstance(acc, AccountInfo):
                continue

            account_id = f"{acc.account_number}:{acc.subaccount_number or '0'}"
            sepa = sepa_lookup.get(account_id)

            route = (
                self._route_from_bank_identifier(acc.bank_identifier)
                if acc.bank_identifier
                else default_route
            )

            owner = AccountOwner(name=acc.owner_name[0]) if acc.owner_name else None

            capabilities = self._capabilities_from_operations(acc.allowed_operations)

            metadata_raw = {
                "account_number": acc.account_number,
                "subaccount_number": acc.subaccount_number or "0",
                "type": str(acc.account_type) if acc.account_type is not None else None,
            }

            domain_accounts.append(
                Account(
                    account_id=account_id,
                    iban=acc.iban,
                    bic=sepa.bic if sepa else acc.bic,
                    currency=acc.currency,
                    product_name=acc.product_name,
                    owner=owner,
                    bank_route=route,
                    capabilities=capabilities,
                    raw_labels=tuple(acc.owner_name),
                    metadata={k: v for k, v in metadata_raw.items() if v is not None},
                )
            )

        logger.warning("Converted %d domain accounts", len(domain_accounts))
        return tuple(domain_accounts)

    def _capabilities_from_operations(
        self,
        allowed_ops: Sequence[str],
    ) -> AccountCapabilities:
        """Convert allowed operations to AccountCapabilities."""
        ops_set = set(allowed_ops)
        return AccountCapabilities(
            can_fetch_balance="HKSAL" in ops_set,
            can_list_transactions="HKKAZ" in ops_set or "HKCAZ" in ops_set,
            can_fetch_statements="HKEKA" in ops_set,
            can_fetch_holdings="HKWPD" in ops_set,
            can_fetch_scheduled_debits="HKDBS" in ops_set or "HKDMB" in ops_set,
        )

    def _route_from_bank_identifier(self, identifier) -> BankRoute:
        """Convert bank identifier to domain BankRoute."""
        if identifier is None:
            return self._credentials.route

        country_numeric = getattr(identifier, "country_identifier", "280")
        country_code = FinTSBankIdentifier.COUNTRY_NUMERIC_TO_ALPHA.get(
            country_numeric,
            country_numeric,
        )
        bank_code = getattr(identifier, "bank_code", self._credentials.route.bank_code)
        return BankRoute(country_code=country_code, bank_code=bank_code)

    @staticmethod
    def _account_key(account: "SEPAAccount") -> str:
        """Create lookup key from SEPA account."""
        return f"{account.accountnumber}:{account.subaccount or '0'}"


__all__ = ["FinTSAccountDiscovery"]
