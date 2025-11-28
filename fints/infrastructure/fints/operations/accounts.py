"""SEPA account discovery operations for FinTS.

This module handles HKSPA/HISPA segment exchanges for discovering
SEPA-enabled accounts from the bank.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from fints.models import SEPAAccount
from fints.segments.accounts import HISPA1, HKSPA1

if TYPE_CHECKING:
    from fints.infrastructure.fints.dialog import Dialog, ProcessedResponse
    from fints.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """
    Basic account information from UPD.

    This is the raw account data from User Parameter Data (HIUPD),
    before enrichment with SEPA details.
    """

    account_number: str
    subaccount_number: str | None
    iban: str | None
    bic: str | None
    currency: str
    owner_name: list[str]
    product_name: str | None
    account_type: str | int | None
    bank_identifier: object  # BankIdentifier from HIUPD
    allowed_operations: list[str]


class AccountOperations:
    """
    Handles SEPA account discovery operations.

    This class provides methods to:
    - Fetch SEPA account details via HKSPA
    - Extract account info from UPD

    Usage:
        ops = AccountOperations(dialog, parameters)
        sepa_accounts = ops.fetch_sepa_accounts()
    """

    def __init__(
        self,
        dialog: "Dialog",
        parameters: "ParameterStore",
    ) -> None:
        """
        Initialize account operations.

        Args:
            dialog: Active dialog for sending requests
            parameters: Parameter store with BPD/UPD
        """
        self._dialog = dialog
        self._parameters = parameters

    def fetch_sepa_accounts(self) -> Sequence[SEPAAccount]:
        """
        Fetch SEPA account information from the bank.

        Sends HKSPA and parses HISPA response to get SEPA-enabled
        accounts with IBAN, BIC, and other details.

        Falls back to UPD if HISPA returns no accounts (some banks
        like DKB only provide account info in UPD).

        Returns:
            List of SEPAAccount objects
        """
        logger.info("Fetching SEPA accounts via HKSPA")

        # Send HKSPA request
        segment = HKSPA1()
        response = self._dialog.send(segment)

        # Extract SEPA accounts from HISPA response
        accounts: list[SEPAAccount] = []

        if response.raw_response is not None:
            for seg in response.raw_response.find_segments(HISPA1):
                if seg.accounts:
                    for acc in seg.accounts:
                        sepa = acc.as_sepa_account()
                        if sepa:
                            accounts.append(sepa)

        # Fallback to UPD if HISPA returned no accounts
        if not accounts:
            logger.info("HISPA returned no accounts, checking UPD")
            upd_accounts = self._parameters.upd.get_accounts()
            for acc in upd_accounts:
                iban = acc.get("iban")
                if iban:
                    accounts.append(
                        SEPAAccount(
                            iban=iban,
                            bic=None,  # BIC not available in UPD
                            accountnumber=acc.get("account_number") or "",
                            subaccount=acc.get("subaccount_number"),
                            blz=None,  # Will be extracted from bank_identifier
                        )
                    )

        logger.info("Found %d SEPA accounts", len(accounts))
        return accounts

    def get_accounts_from_upd(self) -> Sequence[AccountInfo]:
        """
        Extract account information from cached UPD.

        Returns:
            List of AccountInfo objects from User Parameter Data
        """
        upd = self._parameters.upd
        raw_accounts = upd.get_accounts()

        accounts: list[AccountInfo] = []
        for acc in raw_accounts:
            # Extract allowed operations
            allowed_ops = []
            for tx in acc.get("allowed_transactions", []):
                if hasattr(tx, "transaction"):
                    allowed_ops.append(tx.transaction)

            accounts.append(
                AccountInfo(
                    account_number=acc.get("account_number", ""),
                    subaccount_number=acc.get("subaccount_number"),
                    iban=acc.get("iban"),
                    bic=None,  # BIC comes from HISPA, not HIUPD
                    currency=acc.get("currency", "EUR"),
                    owner_name=acc.get("owner_name", []),
                    product_name=acc.get("product_name"),
                    account_type=acc.get("type"),
                    bank_identifier=acc.get("bank_identifier"),
                    allowed_operations=allowed_ops,
                )
            )

        return accounts

    def merge_sepa_info(
        self,
        upd_accounts: Sequence[AccountInfo],
        sepa_accounts: Sequence[SEPAAccount],
    ) -> Sequence[AccountInfo]:
        """
        Merge SEPA details (BIC) into UPD account info.

        Args:
            upd_accounts: Accounts from UPD
            sepa_accounts: SEPA accounts with BIC info

        Returns:
            Updated account info with BIC populated
        """
        # Build lookup by IBAN
        sepa_by_iban = {s.iban: s for s in sepa_accounts if s.iban}

        # Also build lookup by account number for fallback
        sepa_by_number = {
            (s.accountnumber, s.subaccount or ""): s for s in sepa_accounts
        }

        merged = []
        for acc in upd_accounts:
            bic = acc.bic

            # Try to find matching SEPA account
            if acc.iban and acc.iban in sepa_by_iban:
                bic = sepa_by_iban[acc.iban].bic
            elif (acc.account_number, acc.subaccount_number or "") in sepa_by_number:
                sepa = sepa_by_number[(acc.account_number, acc.subaccount_number or "")]
                bic = sepa.bic

            merged.append(
                AccountInfo(
                    account_number=acc.account_number,
                    subaccount_number=acc.subaccount_number,
                    iban=acc.iban,
                    bic=bic,
                    currency=acc.currency,
                    owner_name=acc.owner_name,
                    product_name=acc.product_name,
                    account_type=acc.account_type,
                    bank_identifier=acc.bank_identifier,
                    allowed_operations=acc.allowed_operations,
                )
            )

        return merged

