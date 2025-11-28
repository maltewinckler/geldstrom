"""Gateway that adapts the legacy FinTS client to the new read-only ports."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import hashlib
import logging
from typing import Dict, Iterable, Sequence
from xml.etree import ElementTree as ET
import time as time_module

from fints.application.ports import BankGateway, GatewayCredentials
from fints.client import FinTS3PinTanClient, NeedTANResponse
from fints.exceptions import FinTSUnsupportedOperation
from fints.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceAmount,
    BalanceSnapshot,
    BankCapabilities,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)
from fints.infrastructure.fints import FinTSOperations, SessionState
from fints.models import SEPAAccount
from fints.formals import BankIdentifier as FinTSBankIdentifier


logger = logging.getLogger(__name__)


class FinTSReadOnlyGateway(BankGateway):
    """Adapter keeping the legacy FinTS client behind new read-only ports."""

    def open_session(
        self,
        credentials: GatewayCredentials,
        existing_state: SessionState | None = None,
    ) -> SessionState:
        client = self._build_client(credentials, existing_state)
        with self._logged_in(client):
            client.get_information()
        return self._session_from_client(credentials, client)

    def fetch_bank_capabilities(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
    ) -> BankCapabilities:
        client = self._build_client(credentials, session)
        with self._logged_in(client):
            info = client.get_information()
        return self._capabilities_from_info(info)

    def fetch_accounts(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
    ) -> Sequence[Account]:
        client = self._build_client(credentials, session)
        with self._logged_in(client):
            info = client.get_information()
            sepa_accounts = client.get_sepa_accounts()
        return self._accounts_from_info(credentials.route, info, sepa_accounts)

    def fetch_balance(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
        account: Account,
    ) -> BalanceSnapshot:
        client = self._build_client(credentials, session)
        with self._logged_in(client):
            sepa_account = self._locate_sepa_account(client, account)
            booked = client.get_balance(sepa_account)
        return self._balance_from_mt940(account.account_id, booked)

    def fetch_transactions(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
        account: Account,
        start_date: date | None,
        end_date: date | None,
    ) -> TransactionFeed:
        client = self._build_client(credentials, session)
        with self._logged_in(client):
            sepa_account = self._locate_sepa_account(client, account)
            try:
                transactions = client.get_transactions(
                    sepa_account,
                    start_date,
                    end_date,
                )
                transactions = self._maybe_complete_tan(client, transactions)
                return self._transactions_from_mt940(
                    account.account_id,
                    transactions,
                )
            except FinTSUnsupportedOperation:
                streams = client.get_transactions_xml(
                    sepa_account,
                    start_date,
                    end_date,
                )
                booked_streams, pending_streams = self._maybe_complete_tan(
                    client,
                    streams,
                )
                return self._transactions_from_camt(
                    account.account_id,
                    booked_streams,
                    pending_streams,
                )

    # --- helpers -----------------------------------------------------------------

    def _build_client(
        self,
        credentials: GatewayCredentials,
        state: SessionState | None,
    ) -> FinTS3PinTanClient:
        kwargs: Dict[str, object] = dict(
            bank_identifier=credentials.route.bank_code,
            user_id=credentials.user_id,
            pin=credentials.pin,
            server=credentials.server_url,
            customer_id=credentials.customer_id or credentials.user_id,
            product_id=credentials.product_id,
            product_version=credentials.product_version,
            tan_medium=credentials.tan_medium,
        )
        if state:
            kwargs["from_data"] = state.client_blob
            kwargs["system_id"] = state.system_id
        client = FinTS3PinTanClient(**kwargs)
        if credentials.tan_method:
            client.set_tan_mechanism(credentials.tan_method)
        return client

    @contextmanager
    def _logged_in(self, client: FinTS3PinTanClient):
        with client:
            yield client

    def _session_from_client(
        self,
        credentials: GatewayCredentials,
        client: FinTS3PinTanClient,
    ) -> SessionState:
        blob = client.deconstruct(including_private=True)
        return SessionState(
            route=credentials.route,
            user_id=credentials.user_id,
            system_id=client.system_id,
            client_blob=blob,
            bpd_version=client.bpd_version,
            upd_version=client.upd_version,
        )

    def _capabilities_from_info(self, info: dict) -> BankCapabilities:
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
        sepa_accounts: Sequence[SEPAAccount],
    ) -> Sequence[Account]:
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
        value = ops.get(operation)
        if isinstance(value, bool):
            return value
        return bool(value)

    def _supports_any(self, ops: dict, *operations: FinTSOperations) -> bool:
        return any(self._is_enabled(ops, op) for op in operations)

    def _balance_from_mt940(self, account_id: str, booked) -> BalanceSnapshot:
        amount = Decimal(str(booked.amount.amount))
        booked_amount = BalanceAmount(amount=amount, currency=booked.amount.currency)
        as_of = datetime.combine(booked.date, time.min)
        return BalanceSnapshot(account_id=account_id, as_of=as_of, booked=booked_amount)

    def _transactions_from_mt940(
        self,
        account_id: str,
        transactions: Iterable,
    ) -> TransactionFeed:
        entries = [
            self._transaction_entry(account_id, idx, tx)
            for idx, tx in enumerate(transactions)
        ]
        return self._transaction_feed_from_entries(account_id, entries)

    def _transaction_feed_from_entries(
        self,
        account_id: str,
        entries: Sequence[TransactionEntry],
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
        )

    def _maybe_complete_tan(self, client: FinTS3PinTanClient, response):
        if isinstance(response, NeedTANResponse):
            return self._handle_need_tan_response(client, response)
        return response

    def _handle_need_tan_response(
        self,
        client: FinTS3PinTanClient,
        challenge: NeedTANResponse,
    ):
        if not challenge.decoupled:
            raise RuntimeError(
                "Bank requires manual TAN entry for this operation; "
                "interactive TAN handling is not implemented in the read-only client."
            )
        if challenge.challenge:
            logger.warning(
                "Awaiting approval in bank app: %s",
                challenge.challenge,
            )
        else:
            logger.warning("Awaiting approval in bank app for pending operation.")
        return self._poll_decoupled_confirmation(client, challenge)

    def _poll_decoupled_confirmation(
        self,
        client: FinTS3PinTanClient,
        challenge: NeedTANResponse,
        interval_seconds: float = 2.0,
        max_attempts: int = 30,
    ):
        attempts = 0
        current = challenge
        while attempts < max_attempts:
            if attempts:
                time_module.sleep(interval_seconds)
            result = client.send_tan(current, "")
            if isinstance(result, NeedTANResponse):
                current = result
                attempts += 1
                continue
            return result
        raise TimeoutError(
            "Timed out waiting for decoupled TAN confirmation. "
            "Please confirm the request in your banking app and try again."
        )

    def _transactions_from_camt(
        self,
        account_id: str,
        booked_streams: Iterable[bytes],
        pending_streams: Iterable[bytes],
    ) -> TransactionFeed:
        entries: list[TransactionEntry] = []
        entries.extend(
            self._entries_from_camt_streams(account_id, booked_streams, pending=False)
        )
        entries.extend(
            self._entries_from_camt_streams(account_id, pending_streams, pending=True)
        )
        return self._transaction_feed_from_entries(account_id, entries)

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
            self._parse_camt_date(
                self._find_text(element, namespace, "BookgDt", "Dt")
            )
            or self._parse_camt_date(
                self._find_text(element, namespace, "BookgDt", "DtTm")
            )
            or date.today()
        )
        value_date = (
            self._parse_camt_date(
                self._find_text(element, namespace, "ValDt", "Dt")
            )
            or self._parse_camt_date(
                self._find_text(element, namespace, "ValDt", "DtTm")
            )
            or booking_date
        )
        purpose = self._collect_camt_purpose(element, namespace)
        counterpart_tag = "Dbtr" if indicator.upper() == "CRDT" else "Cdtr"
        counterpart = self._find_text(
            element,
            namespace,
            "NtryDtls",
            "TxDtls",
            "RltdPties",
            counterpart_tag,
            "Nm",
        )
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

    def _collect_camt_purpose(
        self,
        element: ET.Element,
        namespace: str | None,
    ) -> str:
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

    def _extract_xml_namespace(self, element: ET.Element) -> str | None:
        if element.tag.startswith("{"):
            return element.tag[1:].split("}", 1)[0]
        return None

    def _ns(self, namespace: str | None, tag: str) -> str:
        return f"{{{namespace}}}{tag}" if namespace else tag

    def _stable_camt_entry_id(
        self,
        account_id: str,
        element: ET.Element,
    ) -> str:
        payload = ET.tostring(element, encoding="utf-8", method="xml")
        digest = hashlib.sha1(payload).hexdigest()[:12]
        return f"{account_id}-camt-{digest}"

    def _transaction_entry(self, account_id: str, idx: int, tx) -> TransactionEntry:
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
        entry_id = tx.data.get("transaction_reference") or f"{account_id}-{idx}"
        return TransactionEntry(
            entry_id=entry_id,
            booking_date=booking_date,
            value_date=value_date,
            amount=value,
            currency=currency,
            purpose=purpose_text,
            counterpart_name=counterpart,
        )

    def _account_key(self, account: SEPAAccount) -> str:
        return f"{account.accountnumber}:{account.subaccount or '0'}"

    def _locate_sepa_account(
        self,
        client: FinTS3PinTanClient,
        account: Account,
    ) -> SEPAAccount:
        for sepa in client.get_sepa_accounts():
            if self._account_key(sepa) == account.account_id:
                return sepa
        raise ValueError(f"Account {account.account_id} not available from bank")

    def _route_from_identifier(self, identifier) -> BankRoute:
        country_numeric = identifier.country_identifier
        country_code = FinTSBankIdentifier.COUNTRY_NUMERIC_TO_ALPHA.get(
            country_numeric,
            country_numeric,
        )
        return BankRoute(country_code=country_code, bank_code=identifier.bank_code)
