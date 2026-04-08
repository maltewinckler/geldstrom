"""FinTS 3.0 implementation of AccountPort."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel

from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankCapabilities,
    BankRoute,
)
from geldstrom.infrastructure.fints.operations import AccountInfo
from geldstrom.infrastructure.fints.protocol import (
    BankIdentifier as FinTSBankIdentifier,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .base import FinTSServiceBase

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.support.connection import ConnectionContext

logger = logging.getLogger(__name__)


class AccountDiscoveryResult(BaseModel, frozen=True):
    """Accounts plus bank capabilities discovered from one dialog."""

    model_config = {"arbitrary_types_allowed": True}

    accounts: tuple[Account, ...]
    capabilities: BankCapabilities


class FinTSAccountService(FinTSServiceBase):
    """Manages FinTS connections for account discovery; maps results to domain types."""

    def fetch_bank_capabilities(
        self,
        state: FinTSSessionState,
    ) -> BankCapabilities:
        return self.discover(state).capabilities

    def fetch_accounts(
        self,
        state: FinTSSessionState,
    ) -> Sequence[Account]:
        return self.discover(state).accounts

    def discover(
        self,
        state: FinTSSessionState,
    ) -> AccountDiscoveryResult:
        helper = self._make_helper()

        with helper.connect(state) as ctx:
            return self.discover_from_context(ctx)

    def discover_from_context(
        self,
        ctx: ConnectionContext,
    ) -> AccountDiscoveryResult:
        from geldstrom.infrastructure.fints.operations import AccountOperations

        ops = AccountOperations(ctx.dialog, ctx.parameters)
        merged_accounts = ops.fetch_all()
        logger.debug("Fetched %d merged accounts", len(merged_accounts))
        return AccountDiscoveryResult(
            accounts=self.map_accounts_from_operations(
                self._credentials.route,
                merged_accounts,
            ),
            capabilities=self._bank_capabilities_from_parameters(ctx.parameters),
        )

    def map_accounts_from_operations(
        self,
        default_route: BankRoute,
        upd_accounts,
    ) -> tuple[Account, ...]:
        return self._accounts_from_operations(default_route, upd_accounts)

    def _bank_capabilities_from_parameters(self, parameters) -> BankCapabilities:
        supported_ops = parameters.bpd.get_supported_operations()
        supported = {name for name, enabled in supported_ops.items() if enabled}
        return BankCapabilities(
            supported_operations=frozenset(supported),
            supported_formats={},  # TODO: Extract from BPD
        )

    def _accounts_from_operations(
        self,
        default_route: BankRoute,
        upd_accounts,
    ) -> Sequence[Account]:
        domain_accounts: list[Account] = []

        for acc in upd_accounts:
            if not isinstance(acc, AccountInfo):
                continue

            account_id = f"{acc.account_number}:{acc.subaccount_number or '0'}"

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
                    bic=acc.bic,
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


__all__ = ["AccountDiscoveryResult", "FinTSAccountService"]
