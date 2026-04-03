"""SEPA account discovery operations for FinTS."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from geldstrom.infrastructure.fints.exceptions import FinTSSCARequiredError
from geldstrom.infrastructure.fints.protocol import HISPA1, HKSPA1
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog
    from geldstrom.infrastructure.fints.protocol import ParameterStore

# Error code for "Starke Kundenauthentifizierung notwendig" (SCA required)
ERROR_CODE_SCA_REQUIRED = "9075"

logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Raw account data from User Parameter Data (HIUPD)."""

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
    """HKSPA/HISPA-based account discovery."""

    def __init__(
        self,
        dialog: Dialog,
        parameters: ParameterStore,
    ) -> None:
        self._dialog = dialog
        self._parameters = parameters

    def fetch_sepa_accounts(self) -> Sequence[SEPAAccount]:
        """Fetch SEPA accounts via HKSPA; falls back to UPD if bank returns none."""
        logger.info("Fetching SEPA accounts via HKSPA")
        segment = HKSPA1()
        response = self._dialog.send(segment)
        sca_error = response.get_response_by_code(ERROR_CODE_SCA_REQUIRED)
        if sca_error:
            raise FinTSSCARequiredError(
                f"Strong customer authentication required: {sca_error.text}. "
                "Please configure 'tan_method' (and optionally 'tan_medium') "
                "when creating the FinTS3Client. Your bank requires 2FA even "
                "for basic operations like listing accounts."
            )

        accounts: list[SEPAAccount] = []
        if response.raw_response is not None:
            for seg in response.raw_response.find_segments(HISPA1):
                logger.debug("Inspecting HISPA segment %s", seg)
                if seg.accounts:
                    logger.debug("Segment has %d accounts", len(seg.accounts))
                    for acc in seg.accounts:
                        logger.debug("Account data %s", acc)
                        sepa = acc.as_sepa_account()
                        if sepa:
                            logger.debug("Converted to SEPA account %s", sepa)
                            accounts.append(sepa)

        if not accounts:
            logger.info("HISPA returned no accounts, checking UPD")
            upd_accounts = self._parameters.upd.get_accounts()
            for acc in upd_accounts:
                iban = acc.get("iban")
                if iban:
                    accounts.append(
                        SEPAAccount(
                            iban=iban,
                            bic=None,
                            accountnumber=acc.get("account_number") or "",
                            subaccount=acc.get("subaccount_number") or "",
                            blz=None,
                        )
                    )

        logger.info("Found %d SEPA accounts", len(accounts))
        return accounts

    def get_accounts_from_upd(self) -> Sequence[AccountInfo]:
        upd = self._parameters.upd
        raw_accounts = upd.get_accounts()
        accounts: list[AccountInfo] = []
        for acc in raw_accounts:
            allowed_ops = []
            for tx in acc.get("allowed_transactions", []):
                if hasattr(tx, "transaction_code"):
                    allowed_ops.append(tx.transaction_code)
                elif hasattr(tx, "transaction"):
                    allowed_ops.append(tx.transaction)

            accounts.append(
                AccountInfo(
                    account_number=acc.get("account_number", ""),
                    subaccount_number=acc.get("subaccount_number"),
                    iban=acc.get("iban"),
                    bic=None,
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
        sepa_by_iban = {s.iban: s for s in sepa_accounts if s.iban}
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
