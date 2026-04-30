"""CAMT transaction pipeline: HKCAZ → XML parse → TransactionEntry → TransactionFeed.

This module provides the complete data flow for CAMT transaction history:
1. Construct HKCAZ segments with version negotiation
2. Paginate via TouchdownPaginator
3. Parse CAMT XML documents (camt.052 / camt.053)
4. Convert to domain TransactionEntry/TransactionFeed models
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from geldstrom.domain import TransactionEntry, TransactionFeed
from geldstrom.infrastructure.fints.protocol import HKCAZ1, SupportedMessageTypes
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount

from ..helpers import build_account_field, find_highest_supported_version
from ..pagination import TouchdownPaginator
from .feed import build_feed, empty_feed

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog, ProcessedResponse
    from geldstrom.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)

SUPPORTED_HKCAZ = (HKCAZ1,)


# ---------------------------------------------------------------------------
# Fetcher - segments -> domain models
# ---------------------------------------------------------------------------


class CamtFetcher:
    """Fetches CAMT transactions via HKCAZ and converts to domain models."""

    def __init__(
        self,
        dialog: Dialog,
        parameters: ParameterStore,
        max_pages: int = 100,
    ) -> None:
        self._dialog = dialog
        self._parameters = parameters
        self._paginator = TouchdownPaginator(dialog, max_pages=max_pages)

    def fetch(
        self,
        account: SEPAAccount,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
        initial_touchdown: str | None = None,
    ) -> TransactionFeed:
        """Fetch CAMT transactions and return a domain TransactionFeed.

        When *initial_touchdown* is provided the fetcher resumes pagination
        from that point (e.g. after a TAN approval delivered the first page).
        """
        logger.debug(
            "Fetching CAMT transactions for %s from %s to %s (touchdown=%s)",
            account.iban or account.accountnumber,
            start_date,
            end_date,
            initial_touchdown,
        )

        hkcaz_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKCAZ,
            raise_if_missing="Bank does not support CAMT queries (HKCAZ)",
        )
        camt_messages = _get_supported_camt_types(self._parameters)
        if not camt_messages:
            camt_messages = ("urn:iso:std:iso:20022:tech:xsd:camt.052.001.02",)
        supported_messages = SupportedMessageTypes(expected_type=list(camt_messages))
        account_field = build_account_field(hkcaz_class, account)

        booked_docs: list[bytes] = []
        pending_docs: list[bytes] = []

        def segment_factory(touchdown: str | None):
            return hkcaz_class(
                account=account_field,
                supported_camt_messages=supported_messages,
                all_accounts=False,
                date_start=start_date,
                date_end=end_date,
                max_number_responses=None,
                touchdown_point=touchdown,
            )

        def extract_camt(seg) -> tuple[list[bytes], bytes | None] | None:
            booked = []
            pending = None
            stmt = getattr(seg, "statement_booked", None)
            if stmt and hasattr(stmt, "camt_statements"):
                booked = list(stmt.camt_statements)
            if hasattr(seg, "statement_pending"):
                pending = seg.statement_pending
            return (booked, pending) if booked or pending else None

        result = self._paginator.fetch(
            segment_factory=segment_factory,
            response_type="HICAZ",
            extract_items=extract_camt,
            initial_touchdown=initial_touchdown,
        )
        for item in result.items:
            if item:
                booked, pending = item
                booked_docs.extend(booked)
                if pending:
                    pending_docs.append(pending)

        return _camt_to_feed(
            account_id,
            booked_docs,
            pending_docs if include_pending else [],
            has_more=result.has_more,
        )


# ---------------------------------------------------------------------------
# CAMT XML → domain model conversion
# ---------------------------------------------------------------------------


def parse_approved_response(
    response: ProcessedResponse,
    account_id: str,
) -> TransactionFeed:
    """Parse CAMT data from a post-TAN-approval ProcessedResponse."""
    if response.raw_response is None:
        return empty_feed(account_id)
    booked_docs: list[bytes] = []
    pending_docs: list[bytes] = []
    for seg in response.raw_response.find_segments("HICAZ"):
        stmt = getattr(seg, "statement_booked", None)
        if stmt and hasattr(stmt, "camt_statements"):
            booked_docs.extend(stmt.camt_statements)
        pending = getattr(seg, "statement_pending", None)
        if pending:
            pending_docs.append(pending)
    if not booked_docs and not pending_docs:
        return empty_feed(account_id)
    return _camt_to_feed(account_id, booked_docs, pending_docs, has_more=False)


def _camt_to_feed(
    account_id: str,
    booked_streams: Iterable[bytes],
    pending_streams: Iterable[bytes],
    *,
    has_more: bool = False,
) -> TransactionFeed:
    """Convert CAMT XML streams to a domain TransactionFeed."""
    entries: list[TransactionEntry] = []
    entries.extend(_entries_from_streams(account_id, booked_streams, pending=False))
    entries.extend(_entries_from_streams(account_id, pending_streams, pending=True))
    return build_feed(account_id, entries, has_more=has_more)


def _entries_from_streams(
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
        collected.extend(_entries_from_document(account_id, blob, pending))
    return tuple(collected)


def _entries_from_document(
    account_id: str,
    payload: bytes,
    pending: bool,
) -> Sequence[TransactionEntry]:
    try:
        root = ET.fromstring(payload)  # noqa: S314
    except ET.ParseError:
        return ()

    namespace = _extract_xml_namespace(root)
    entry_tag = f".//{_ns(namespace, 'Ntry')}"
    entries: list[TransactionEntry] = []

    for element in root.findall(entry_tag):
        entry = _camt_element_to_entry(account_id, element, pending, namespace)
        if entry:
            entries.append(entry)

    return tuple(entries)


def _camt_element_to_entry(
    account_id: str,
    element: ET.Element,
    pending: bool,
    namespace: str | None,
) -> TransactionEntry | None:
    if logger.isEnabledFor(logging.DEBUG):
        _log_camt_element(element, namespace)

    amount_elem = element.find(_ns(namespace, "Amt"))
    if amount_elem is None or not amount_elem.text:
        return None

    try:
        value = Decimal(amount_elem.text.strip())
    except (InvalidOperation, ValueError):
        return None

    indicator = element.findtext(_ns(namespace, "CdtDbtInd")) or ""
    if indicator.upper() == "DBIT":
        value = -value

    currency = amount_elem.attrib.get("Ccy", "EUR")

    booking_date = (
        _parse_camt_date(_find_text(element, namespace, "BookgDt", "Dt"))
        or _parse_camt_date(_find_text(element, namespace, "BookgDt", "DtTm"))
        or date.today()
    )

    value_date = (
        _parse_camt_date(_find_text(element, namespace, "ValDt", "Dt"))
        or _parse_camt_date(_find_text(element, namespace, "ValDt", "DtTm"))
        or booking_date
    )

    purpose = _collect_camt_purpose(element, namespace)

    counterpart_tag = "Dbtr" if indicator.upper() == "CRDT" else "Cdtr"
    counterpart = _find_counterpart_name(element, namespace, counterpart_tag)

    counterpart_iban = _find_text(
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
        counterpart_iban = _find_text(
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
        _find_text(element, namespace, "AcctSvcrRef")
        or _find_text(element, namespace, "NtryRef")
        or _find_text(
            element,
            namespace,
            "NtryDtls",
            "TxDtls",
            "Refs",
            "EndToEndId",
        )
        or _stable_camt_entry_id(account_id, element)
    )

    metadata: dict[str, str] = {}
    if pending:
        metadata["pending"] = "true"

    status = _find_text(element, namespace, "Sts")
    if status:
        metadata["status"] = status

    if indicator:
        metadata["direction"] = indicator

    ref_owner = _find_text(
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


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _find_counterpart_name(
    element: ET.Element,
    namespace: str | None,
    counterpart_tag: str,
) -> str | None:
    rltd_pties = element.find(
        f".//{_ns(namespace, 'NtryDtls')}/{_ns(namespace, 'TxDtls')}"
        f"/{_ns(namespace, 'RltdPties')}"
    )
    if rltd_pties is None:
        return None
    party_tags = [counterpart_tag, f"Ultmt{counterpart_tag}"]

    for tag in party_tags:
        party_elem = rltd_pties.find(_ns(namespace, tag))
        if party_elem is not None:
            nm_elem = party_elem.find(f".//{_ns(namespace, 'Nm')}")
            if nm_elem is not None and nm_elem.text:
                name = nm_elem.text.strip()
                if name:
                    return name

    return None


def _collect_camt_purpose(
    element: ET.Element,
    namespace: str | None,
) -> str:
    parts: list[str] = []

    add_info = _find_text(element, namespace, "AddtlNtryInf")
    if add_info:
        parts.append(add_info)

    remittance_tag = f".//{_ns(namespace, 'Ustrd')}"
    for remittance in element.findall(remittance_tag):
        if remittance.text:
            text = remittance.text.strip()
            if text:
                parts.append(text)

    return " ".join(parts).strip()


def _find_text(
    element: ET.Element,
    namespace: str | None,
    *path: str,
) -> str | None:
    node = element
    for tag in path:
        node = node.find(_ns(namespace, tag))
        if node is None:
            return None
    if node.text:
        text = node.text.strip()
        return text or None
    return None


def _parse_camt_date(value: str | None) -> date | None:
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


def _extract_xml_namespace(element: ET.Element) -> str | None:
    if element.tag.startswith("{"):
        return element.tag[1:].split("}", 1)[0]
    return None


def _ns(namespace: str | None, tag: str) -> str:
    return f"{{{namespace}}}{tag}" if namespace else tag


def _stable_camt_entry_id(account_id: str, element: ET.Element) -> str:
    payload = ET.tostring(element, encoding="utf-8", method="xml")
    digest = hashlib.sha1(payload).hexdigest()[:12]  # noqa: S324
    return f"{account_id}-camt-{digest}"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _get_supported_camt_types(parameters: ParameterStore) -> tuple[str, ...]:
    segment = parameters.bpd.find_segment("HICAZS")
    if not segment:
        return ()
    identifiers: list[str] = []
    _collect_camt_identifiers(segment, identifiers)
    seen: set[str] = set()
    ordered: list[str] = []
    for ident in identifiers:
        if ident not in seen:
            seen.add(ident)
            ordered.append(ident)
    return tuple(ordered)


def _collect_camt_identifiers(node, bucket: list[str]) -> None:
    if node is None:
        return

    if isinstance(node, str):
        if "camt." in node.lower():
            bucket.append(node)
        return

    if isinstance(node, (bytes, bytearray)):
        return

    if isinstance(node, Iterable) and not isinstance(node, str):
        for item in node:
            _collect_camt_identifiers(item, bucket)
        return
    model_fields = getattr(node, "model_fields", None)
    if model_fields:
        for name in model_fields:
            _collect_camt_identifiers(getattr(node, name, None), bucket)


def _log_camt_element(element: ET.Element, namespace: str | None) -> None:
    logger.debug("CAMT Entry - Checking counterparty locations:")
    rltd_pties = element.find(
        f".//{_ns(namespace, 'NtryDtls')}/{_ns(namespace, 'TxDtls')}"
        f"/{_ns(namespace, 'RltdPties')}"
    )
    if rltd_pties is None:
        logger.debug("  RltdPties: NOT FOUND")
        return
    logger.debug("  RltdPties: FOUND")
    party_tags = ["Dbtr", "Cdtr", "UltmtDbtr", "UltmtCdtr"]
    for tag in party_tags:
        party_elem = rltd_pties.find(_ns(namespace, tag))
        if party_elem is not None:
            name = party_elem.findtext(_ns(namespace, "Nm"))
            logger.debug("  %s/Nm: %s", tag, name or "(empty)")
            pty_elem = party_elem.find(_ns(namespace, "Pty"))
            if pty_elem is not None:
                pty_name = pty_elem.findtext(_ns(namespace, "Nm"))
                logger.debug("  %s/Pty/Nm: %s", tag, pty_name or "(empty)")
            pstl_addr = party_elem.find(_ns(namespace, "PstlAdr"))
            if pstl_addr is not None:
                addr_name = pstl_addr.findtext(_ns(namespace, "Nm"))
                logger.debug("  %s/PstlAdr/Nm: %s", tag, addr_name or "(empty)")
        else:
            logger.debug("  %s: NOT FOUND", tag)

    acct_tags = ["DbtrAcct", "CdtrAcct"]
    for tag in acct_tags:
        acct_elem = rltd_pties.find(_ns(namespace, tag))
        if acct_elem is not None:
            iban = _find_text(rltd_pties, namespace, tag, "Id", "IBAN")
            logger.debug("  %s/Id/IBAN: %s", tag, iban or "(empty)")

    addtl_info = element.findtext(_ns(namespace, "AddtlNtryInf"))
    if addtl_info:
        truncated = addtl_info[:100] + "..." if len(addtl_info) > 100 else addtl_info
        logger.debug("  AddtlNtryInf: %s", truncated)
