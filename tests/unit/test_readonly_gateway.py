"""Tests for the infrastructure adapter helpers.

This file tests adapter parsing functionality that supports the
FinTS3Client.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from geldstrom.domain import BankRoute
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount


# --------------------------------------------------------------------------
# Adapter Helper Tests - test parsing logic in adapters
# --------------------------------------------------------------------------


def test_transactions_adapter_camt_parsing():
    """Test CAMT parsing through the transaction adapter."""
    from geldstrom.infrastructure.fints.adapters.transactions import (
        FinTSTransactionHistory,
    )

    # Create adapter instance (doesn't need real credentials for parsing tests)
    creds = MagicMock()
    adapter = FinTSTransactionHistory(creds)

    document = _build_camt_document(
        amount="123.45",
        indicator="CRDT",
        entry_id="ABC123",
        addtl_info="Sample booking",
        remittance="Invoice 42",
        counterpart_name="Payee Name",
        counterpart_iban="DE001234",
    )

    feed = adapter._transactions_from_camt("acct-1", [document], [])

    assert feed.account_id == "acct-1"
    assert feed.start_date == date(2025, 1, 10)
    assert feed.end_date == date(2025, 1, 10)
    assert len(feed.entries) == 1

    entry = feed.entries[0]
    assert entry.amount == Decimal("123.45")
    assert entry.booking_date == date(2025, 1, 10)
    assert entry.value_date == date(2025, 1, 9)
    assert entry.purpose == "Sample booking Invoice 42"
    assert entry.counterpart_name == "Payee Name"
    assert entry.counterpart_iban == "DE001234"
    assert entry.entry_id == "ABC123"
    assert entry.metadata["direction"] == "CRDT"


def test_transactions_adapter_pending_entries():
    """Test pending entry parsing through transaction adapter."""
    from geldstrom.infrastructure.fints.adapters.transactions import (
        FinTSTransactionHistory,
    )

    creds = MagicMock()
    adapter = FinTSTransactionHistory(creds)

    document = _build_camt_document(
        amount="50.00",
        indicator="DBIT",
        entry_id="PENDING",
        addtl_info="Pending entry",
        remittance="Not booked",
        counterpart_name="Merchant",
        counterpart_iban="DE009999",
    )

    feed = adapter._transactions_from_camt("acct-2", [], [document])

    assert len(feed.entries) == 1
    entry = feed.entries[0]
    assert entry.amount == Decimal("-50.00")
    assert entry.metadata["pending"] == "true"
    assert entry.metadata["direction"] == "DBIT"


def test_accounts_adapter_capabilities_from_operations():
    """Test capability extraction through accounts adapter."""
    from geldstrom.infrastructure.fints.adapters.accounts import FinTSAccountDiscovery

    creds = MagicMock()
    adapter = FinTSAccountDiscovery(creds)

    # Test with allowed operations as list of segment type strings
    allowed_ops = ["HKSAL", "HKKAZ", "HKEKA"]

    capabilities = adapter._capabilities_from_operations(allowed_ops)

    assert capabilities.can_fetch_balance
    assert capabilities.can_list_transactions
    assert capabilities.can_fetch_statements
    assert not capabilities.can_fetch_holdings


def test_accounts_adapter_merges_sepa_metadata():
    """Test account info merging through accounts adapter."""
    from geldstrom.infrastructure.fints.adapters.accounts import FinTSAccountDiscovery
    from geldstrom.infrastructure.fints.operations import AccountInfo

    creds = MagicMock()
    creds.route = BankRoute(country_code="DE", bank_code="50030000")
    adapter = FinTSAccountDiscovery(creds)

    default_route = BankRoute(country_code="DE", bank_code="50030000")

    upd_accounts = [
        AccountInfo(
            account_number="123456",
            subaccount_number="0",
            iban="DE001234",
            bic=None,
            currency="EUR",
            owner_name=["Alice"],
            product_name="Checking",
            account_type=1,
            bank_identifier=None,
            allowed_operations=["HKSAL", "HKCAZ"],
        )
    ]

    sepa_accounts = [
        SEPAAccount(
            iban="DE001234",
            bic="BANKDEFFXXX",
            accountnumber="123456",
            subaccount="0",
            blz="50030000",
        )
    ]

    accounts = adapter._accounts_from_operations(
        default_route, upd_accounts, sepa_accounts
    )

    assert len(accounts) == 1
    account = accounts[0]
    assert account.account_id == "123456:0"
    assert account.owner.name == "Alice"
    assert account.bic == "BANKDEFFXXX"
    assert account.supports_transactions()


def test_balance_adapter_operations_parsing():
    """Test balance parsing through balance adapter."""
    from geldstrom.infrastructure.fints.adapters.balances import FinTSBalanceAdapter
    from geldstrom.infrastructure.fints.operations import BalanceResult, MT940Balance

    creds = MagicMock()
    adapter = FinTSBalanceAdapter(creds)

    result = BalanceResult(
        booked=MT940Balance(
            amount=Decimal("10.00"),
            currency="EUR",
            date=date(2024, 1, 5),
            status="C",  # Credit
        ),
        pending=None,
        available=None,
    )

    snapshot = adapter._balance_from_operations("acct", result)

    assert snapshot.account_id == "acct"
    assert snapshot.booked.amount == Decimal("10.00")
    assert snapshot.as_of.date() == date(2024, 1, 5)


def test_transactions_adapter_mt940_parsing():
    """Test MT940 transaction parsing through transaction adapter."""
    from geldstrom.infrastructure.fints.adapters.transactions import (
        FinTSTransactionHistory,
    )

    creds = MagicMock()
    adapter = FinTSTransactionHistory(creds)

    txns = [
        SimpleNamespace(
            data={
                "amount": SimpleNamespace(amount=Decimal("1.00"), currency="EUR"),
                "date": date(2024, 1, 2),
                "entry_date": date(2024, 1, 1),
                "purpose": ["Line", "One"],
                "applicant_name": "Alice",
                "transaction_reference": "REF-1",
            }
        ),
        SimpleNamespace(
            data={
                "amount": SimpleNamespace(amount=Decimal("-2.00"), currency="EUR"),
                "date": date(2024, 1, 5),
                "purpose": "Single",
                "beneficiary": "Bob",
            }
        ),
    ]

    feed = adapter._transactions_from_mt940("acct", txns)

    assert feed.start_date == date(2024, 1, 2)
    assert feed.end_date == date(2024, 1, 5)
    assert feed.entries[0].purpose == "Line One"
    assert feed.entries[1].amount == Decimal("-2")


def test_accounts_adapter_route_from_bank_identifier():
    """Test route parsing through accounts adapter."""
    from geldstrom.infrastructure.fints.adapters.accounts import FinTSAccountDiscovery

    creds = MagicMock()
    creds.route = BankRoute(country_code="DE", bank_code="50030000")
    adapter = FinTSAccountDiscovery(creds)

    identifier = SimpleNamespace(country_identifier="280", bank_code="50010517")

    route = adapter._route_from_bank_identifier(identifier)

    assert route.country_code == "DE"
    assert route.bank_code == "50010517"


# --------------------------------------------------------------------------
# Test Helpers
# --------------------------------------------------------------------------


def _build_camt_document(
    amount: str,
    indicator: str,
    entry_id: str,
    addtl_info: str,
    remittance: str,
    counterpart_name: str,
    counterpart_iban: str,
    booking_date: str = "2025-01-10",
    value_date: str = "2025-01-09",
) -> bytes:
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<Document xmlns='urn:iso:std:iso:20022:tech:xsd:camt.052.001.08'>
  <BkToCstmrAcctRpt>
    <Rpt>
      <Ntry>
        <Amt Ccy='EUR'>{amount}</Amt>
        <CdtDbtInd>{indicator}</CdtDbtInd>
        <BookgDt><Dt>{booking_date}</Dt></BookgDt>
        <ValDt><Dt>{value_date}</Dt></ValDt>
        <AddtlNtryInf>{addtl_info}</AddtlNtryInf>
        <NtryDtls>
          <TxDtls>
            <Refs>
              <EndToEndId>{entry_id}</EndToEndId>
            </Refs>
            <RltdPties>
              <Dbtr>
                <Nm>{counterpart_name}</Nm>
              </Dbtr>
              <DbtrAcct>
                <Id>
                  <IBAN>{counterpart_iban}</IBAN>
                </Id>
              </DbtrAcct>
            </RltdPties>
            <RmtInf>
              <Ustrd>{remittance}</Ustrd>
            </RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
    </Rpt>
  </BkToCstmrAcctRpt>
</Document>
""".encode("utf-8")
