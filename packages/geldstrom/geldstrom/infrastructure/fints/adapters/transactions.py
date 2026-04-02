"""FinTS 3.0 implementation of TransactionHistoryPort."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from geldstrom.domain import TransactionEntry, TransactionFeed
from geldstrom.domain.connection import ChallengeHandler, TANConfig
from geldstrom.domain.ports.transactions import TransactionHistoryPort
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.exceptions import FinTSUnsupportedOperation
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper
from .helpers import locate_sepa_account

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FinTSTransactionHistory(TransactionHistoryPort):
    """FinTS 3.0 implementation of TransactionHistoryPort via HKKAZ/HKCAZ segments."""

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

    def fetch_history(
        self,
        state: FinTSSessionState,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ) -> TransactionFeed:
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            TransactionOperations,
        )

        helper = FinTSConnectionHelper(
            self._credentials,
            tan_config=self._tan_config,
            challenge_handler=self._challenge_handler,
        )

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            tx_ops = TransactionOperations(ctx.dialog, ctx.parameters)
            sepa_account = locate_sepa_account(account_ops, account_id)
            # Prefer CAMT when pending transactions are needed (only format that supports it);
            # otherwise prefer MT940 (more widely supported).
            if include_pending:
                return self._fetch_with_camt_preferred(
                    tx_ops,
                    sepa_account,
                    account_id,
                    start_date,
                    end_date,
                    include_pending,
                )
            else:
                return self._fetch_with_mt940_preferred(
                    tx_ops, sepa_account, account_id, start_date, end_date
                )

    def _fetch_with_mt940_preferred(
        self,
        tx_ops,
        sepa_account,
        account_id: str,
        start_date: date | None,
        end_date: date | None,
    ) -> TransactionFeed:
        """Fetch transactions preferring MT940, falling back to CAMT."""
        try:
            result = tx_ops.fetch_mt940(sepa_account, start_date, end_date)
            return self._transactions_from_mt940(
                account_id, result.transactions, has_more=result.has_more
            )
        except FinTSUnsupportedOperation:
            result = tx_ops.fetch_camt(sepa_account, start_date, end_date)
            return self._transactions_from_camt(
                account_id,
                result.booked_documents,
                pending_streams=[],
                has_more=result.has_more,
            )

    def _fetch_with_camt_preferred(
        self,
        tx_ops,
        sepa_account,
        account_id: str,
        start_date: date | None,
        end_date: date | None,
        include_pending: bool,
    ) -> TransactionFeed:
        try:
            result = tx_ops.fetch_camt(sepa_account, start_date, end_date)
            return self._transactions_from_camt(
                account_id,
                result.booked_documents,
                result.pending_documents if include_pending else [],
                has_more=result.has_more,
            )
        except FinTSUnsupportedOperation:
            logger.warning(
                "Bank does not support CAMT; falling back to MT940 "
                "(pending transactions will not be included)"
            )
            result = tx_ops.fetch_mt940(sepa_account, start_date, end_date)
            return self._transactions_from_mt940(
                account_id, result.transactions, has_more=result.has_more
            )

    def _transactions_from_mt940(
        self,
        account_id: str,
        transactions: Iterable,
        *,
        has_more: bool = False,
    ) -> TransactionFeed:
        entries = [
            self._transaction_entry(account_id, idx, tx)
            for idx, tx in enumerate(transactions)
        ]
        return self._transaction_feed_from_entries(
            account_id, entries, has_more=has_more
        )

    def _transaction_entry(
        self,
        account_id: str,
        idx: int,
        tx,
    ) -> TransactionEntry:
        if logger.isEnabledFor(logging.DEBUG):
            self._log_mt940_fields(tx, idx)

        amount = tx.data.get("amount")
        value = Decimal(str(getattr(amount, "amount", "0")))
        currency = getattr(amount, "currency", "EUR")

        booking_date = tx.data.get("date") or tx.data.get("entry_date") or date.today()
        value_date = tx.data.get("entry_date") or booking_date

        purpose = tx.data.get("purpose")
        if isinstance(purpose, list):
            purpose_text = " ".join(str(p) for p in purpose if p)
        else:
            purpose_text = str(purpose or "")

        counterpart = tx.data.get("applicant_name") or tx.data.get("beneficiary")
        counterpart_iban = tx.data.get("applicant_iban")
        entry_id = tx.data.get("transaction_reference") or f"{account_id}-{idx}"

        return TransactionEntry(
            entry_id=entry_id,
            booking_date=booking_date,
            value_date=value_date,
            amount=value,
            currency=currency,
            purpose=purpose_text,
            counterpart_name=counterpart,
            counterpart_iban=counterpart_iban,
        )

    def _transactions_from_camt(
        self,
        account_id: str,
        booked_streams: Iterable[bytes],
        pending_streams: Iterable[bytes],
        *,
        has_more: bool = False,
    ) -> TransactionFeed:
        entries: list[TransactionEntry] = []

        entries.extend(
            self._entries_from_camt_streams(account_id, booked_streams, pending=False)
        )
        entries.extend(
            self._entries_from_camt_streams(account_id, pending_streams, pending=True)
        )

        return self._transaction_feed_from_entries(
            account_id, entries, has_more=has_more
        )

    def _entries_from_camt_streams(
        self,
        account_id: str,
        streams: Iterable[bytes] | None,
        pending: bool,
    ) -> Sequence[TransactionEntry]:
        if not streams:
            return ()

        collected: list[TransactionEntry] = []

        for blob in streams:
            if not blob:
                continue
            collected.extend(
                self._entries_from_camt_document(account_id, blob, pending)
            )

        return tuple(collected)

    def _entries_from_camt_document(
        self,
        account_id: str,
        payload: bytes,
        pending: bool,
    ) -> Sequence[TransactionEntry]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return ()

        namespace = self._extract_xml_namespace(root)
        entry_tag = f".//{self._ns(namespace, 'Ntry')}"
        entries: list[TransactionEntry] = []

        for element in root.findall(entry_tag):
            entry = self._transaction_entry_from_camt_element(
                account_id,
                element,
                pending,
                namespace,
            )
            if entry:
                entries.append(entry)

        return tuple(entries)

    def _transaction_entry_from_camt_element(
        self,
        account_id: str,
        element: ET.Element,
        pending: bool,
        namespace: str | None,
    ) -> TransactionEntry | None:
        if logger.isEnabledFor(logging.DEBUG):
            self._log_camt_element(element, namespace)

        amount_elem = element.find(self._ns(namespace, "Amt"))
        if amount_elem is None or not amount_elem.text:
            return None

        try:
            value = Decimal(amount_elem.text.strip())
        except (InvalidOperation, ValueError):
            return None

        indicator = element.findtext(self._ns(namespace, "CdtDbtInd")) or ""
        if indicator.upper() == "DBIT":
            value = -value

        currency = amount_elem.attrib.get("Ccy", "EUR")

        booking_date = (
            self._parse_camt_date(self._find_text(element, namespace, "BookgDt", "Dt"))
            or self._parse_camt_date(
                self._find_text(element, namespace, "BookgDt", "DtTm")
            )
            or date.today()
        )

        value_date = (
            self._parse_camt_date(self._find_text(element, namespace, "ValDt", "Dt"))
            or self._parse_camt_date(
                self._find_text(element, namespace, "ValDt", "DtTm")
            )
            or booking_date
        )

        purpose = self._collect_camt_purpose(element, namespace)

        counterpart_tag = "Dbtr" if indicator.upper() == "CRDT" else "Cdtr"
        counterpart = self._find_counterpart_name(element, namespace, counterpart_tag)

        counterpart_iban = self._find_text(
            element,
            namespace,
            "NtryDtls",
            "TxDtls",
            "RltdPties",
            f"{counterpart_tag}Acct",
            "Id",
            "IBAN",
        )

        if not counterpart_iban:
            counterpart_iban = self._find_text(
                element,
                namespace,
                "NtryDtls",
                "TxDtls",
                "RltdPties",
                f"{counterpart_tag}Acct",
                "Id",
                "Othr",
                "Id",
            )

        entry_id = (
            self._find_text(element, namespace, "AcctSvcrRef")
            or self._find_text(element, namespace, "NtryRef")
            or self._find_text(
                element,
                namespace,
                "NtryDtls",
                "TxDtls",
                "Refs",
                "EndToEndId",
            )
            or self._stable_camt_entry_id(account_id, element)
        )

        metadata: dict[str, str] = {}
        if pending:
            metadata["pending"] = "true"

        status = self._find_text(element, namespace, "Sts")
        if status:
            metadata["status"] = status

        if indicator:
            metadata["direction"] = indicator

        ref_owner = self._find_text(
            element,
            namespace,
            "NtryDtls",
            "TxDtls",
            "Refs",
            "AcctSvcrRef",
        )
        if ref_owner:
            metadata["service_reference"] = ref_owner

        return TransactionEntry(
            entry_id=entry_id,
            booking_date=booking_date,
            value_date=value_date,
            amount=value,
            currency=currency,
            purpose=purpose,
            counterpart_name=counterpart,
            counterpart_iban=counterpart_iban,
            metadata=metadata,
        )

    def _find_counterpart_name(
        self,
        element: ET.Element,
        namespace: str | None,
        counterpart_tag: str,
    ) -> str | None:
        """Find counterpart name from CAMT party elements."""
        rltd_pties = element.find(
            f".//{self._ns(namespace, 'NtryDtls')}/{self._ns(namespace, 'TxDtls')}"
            f"/{self._ns(namespace, 'RltdPties')}"
        )
        if rltd_pties is None:
            return None
        party_tags = [counterpart_tag, f"Ultmt{counterpart_tag}"]

        for tag in party_tags:
            party_elem = rltd_pties.find(self._ns(namespace, tag))
            if party_elem is not None:
                nm_elem = party_elem.find(f".//{self._ns(namespace, 'Nm')}")
                if nm_elem is not None and nm_elem.text:
                    name = nm_elem.text.strip()
                    if name:
                        return name

        return None

    def _collect_camt_purpose(
        self,
        element: ET.Element,
        namespace: str | None,
    ) -> str:
        """Collect purpose text from CAMT entry."""
        parts: list[str] = []

        add_info = self._find_text(element, namespace, "AddtlNtryInf")
        if add_info:
            parts.append(add_info)

        remittance_tag = f".//{self._ns(namespace, 'Ustrd')}"
        for remittance in element.findall(remittance_tag):
            if remittance.text:
                text = remittance.text.strip()
                if text:
                    parts.append(text)

        return " ".join(parts).strip()

    def _find_text(
        self,
        element: ET.Element,
        namespace: str | None,
        *path: str,
    ) -> str | None:
        """Find text at nested XML path."""
        node = element
        for tag in path:
            node = node.find(self._ns(namespace, tag))
            if node is None:
                return None
        if node.text:
            text = node.text.strip()
            return text or None
        return None

    def _parse_camt_date(self, value: str | None) -> date | None:
        """Parse date from CAMT format."""
        if not value:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        normalized = normalized.replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            pass

        try:
            return datetime.strptime(normalized[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def _log_mt940_fields(self, tx, idx: int) -> None:
        logger.debug("MT940 Transaction #%d - Available fields:", idx)
        for key, value in tx.data.items():
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            logger.debug("  %s: %s", key, value_str)

    def _log_camt_element(self, element: ET.Element, namespace: str | None) -> None:
        logger.debug("CAMT Entry - Checking counterparty locations:")
        rltd_pties = element.find(
            f".//{self._ns(namespace, 'NtryDtls')}/{self._ns(namespace, 'TxDtls')}"
            f"/{self._ns(namespace, 'RltdPties')}"
        )
        if rltd_pties is None:
            logger.debug("  RltdPties: NOT FOUND")
            return
        logger.debug("  RltdPties: FOUND")
        party_tags = ["Dbtr", "Cdtr", "UltmtDbtr", "UltmtCdtr"]
        for tag in party_tags:
            party_elem = rltd_pties.find(self._ns(namespace, tag))
            if party_elem is not None:
                # Direct name
                name = party_elem.findtext(self._ns(namespace, "Nm"))
                logger.debug("  %s/Nm: %s", tag, name or "(empty)")
                pty_elem = party_elem.find(self._ns(namespace, "Pty"))
                if pty_elem is not None:
                    pty_name = pty_elem.findtext(self._ns(namespace, "Nm"))
                    logger.debug("  %s/Pty/Nm: %s", tag, pty_name or "(empty)")
                pstl_addr = party_elem.find(self._ns(namespace, "PstlAdr"))
                if pstl_addr is not None:
                    addr_name = pstl_addr.findtext(self._ns(namespace, "Nm"))
                    logger.debug("  %s/PstlAdr/Nm: %s", tag, addr_name or "(empty)")
            else:
                logger.debug("  %s: NOT FOUND", tag)

        acct_tags = ["DbtrAcct", "CdtrAcct"]
        for tag in acct_tags:
            acct_elem = rltd_pties.find(self._ns(namespace, tag))
            if acct_elem is not None:
                iban = self._find_text(rltd_pties, namespace, tag, "Id", "IBAN")
                logger.debug("  %s/Id/IBAN: %s", tag, iban or "(empty)")

        addtl_info = element.findtext(self._ns(namespace, "AddtlNtryInf"))
        if addtl_info:
            truncated = (
                addtl_info[:100] + "..." if len(addtl_info) > 100 else addtl_info
            )
            logger.debug("  AddtlNtryInf: %s", truncated)

    @staticmethod
    def _extract_xml_namespace(element: ET.Element) -> str | None:
        if element.tag.startswith("{"):
            return element.tag[1:].split("}", 1)[0]
        return None

    @staticmethod
    def _ns(namespace: str | None, tag: str) -> str:
        return f"{{{namespace}}}{tag}" if namespace else tag

    def _stable_camt_entry_id(
        self,
        account_id: str,
        element: ET.Element,
    ) -> str:
        """Generate stable ID for CAMT entry without explicit ID."""
        payload = ET.tostring(element, encoding="utf-8", method="xml")
        digest = hashlib.sha1(payload).hexdigest()[:12]
        return f"{account_id}-camt-{digest}"

    def _transaction_feed_from_entries(
        self,
        account_id: str,
        entries: Sequence[TransactionEntry],
        *,
        has_more: bool = False,
    ) -> TransactionFeed:
        if entries:
            start_date = min(entry.booking_date for entry in entries)
            end_date = max(entry.booking_date for entry in entries)
        else:
            today = datetime.now().date()
            start_date = end_date = today

        return TransactionFeed(
            account_id=account_id,
            entries=tuple(entries),
            start_date=start_date,
            end_date=end_date,
            has_more=has_more,
        )


__all__ = ["FinTSTransactionHistory"]
