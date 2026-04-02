"""FinTS 3.0 implementation of AccountDiscoveryPort."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankCapabilities,
    BankRoute,
)
from geldstrom.domain.connection import ChallengeHandler, TANConfig
from geldstrom.domain.ports.accounts import AccountDiscoveryPort
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.operations import AccountInfo
from geldstrom.infrastructure.fints.protocol import (
    BankIdentifier as FinTSBankIdentifier,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper
from .helpers import account_key

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount

logger = logging.getLogger(__name__)


class FinTSAccountDiscovery(AccountDiscoveryPort):
    """FinTS 3.0 implementation of AccountDiscoveryPort."""

    def __init__(
        self,
        credentials: GatewayCredentials,
        *,
        tan_config: TANConfig | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        self._credentials = credentials
        self._tan_config = tan_config or TANConfig()
        self._challenge_handler = challenge_handler

    def fetch_bank_capabilities(
        self,
        state: FinTSSessionState,
    ) -> BankCapabilities:
        helper = FinTSConnectionHelper(
            self._credentials,
            tan_config=self._tan_config,
            challenge_handler=self._challenge_handler,
        )

        with helper.connect(state) as ctx:
            supported_ops = ctx.parameters.bpd.get_supported_operations()
            supported = {name for name, enabled in supported_ops.items() if enabled}
            return BankCapabilities(
                supported_operations=frozenset(supported),
                supported_formats={},  # TODO: Extract from BPD
            )

    def fetch_accounts(
        self,
        state: FinTSSessionState,
    ) -> Sequence[Account]:
        from geldstrom.infrastructure.fints.operations import AccountOperations

        helper = FinTSConnectionHelper(
            self._credentials,
            tan_config=self._tan_config,
            challenge_handler=self._challenge_handler,
        )

        with helper.connect(state) as ctx:
            ops = AccountOperations(ctx.dialog, ctx.parameters)
            sepa_accounts = ops.fetch_sepa_accounts()
            upd_accounts = list(ops.get_accounts_from_upd())
            if not upd_accounts and sepa_accounts:
                logger.info(
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
            logger.debug(
                "Fetched %d SEPA accounts, %d UPD accounts",
                len(sepa_accounts),
                len(upd_accounts),
            )

            return self._accounts_from_operations(
                self._credentials.route,
                upd_accounts,
                sepa_accounts,
            )

    def _accounts_from_operations(
        self,
        default_route: BankRoute,
        upd_accounts,
        sepa_accounts: Sequence[SEPAAccount],
    ) -> Sequence[Account]:

        sepa_lookup = {account_key(sepa): sepa for sepa in sepa_accounts}
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

        logger.debug("Converted %d domain accounts", len(domain_accounts))
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


__all__ = ["FinTSAccountDiscovery"]
