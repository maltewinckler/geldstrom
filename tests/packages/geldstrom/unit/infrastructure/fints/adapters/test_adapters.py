"""Tests for the infrastructure adapter helpers.

This file tests adapter parsing functionality that supports the
FinTS3Client.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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
    allowed_ops = ["HKSAL", "HKKAZ"]

    capabilities = adapter._capabilities_from_operations(allowed_ops)

    assert capabilities.can_fetch_balance
    assert capabilities.can_list_transactions
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


def test_balance_adapter_maps_all_optional_fields():
    """Test that pending, available, and credit_limit are mapped."""
    from geldstrom.infrastructure.fints.adapters.balances import FinTSBalanceAdapter
    from geldstrom.infrastructure.fints.operations import BalanceResult, MT940Balance

    creds = MagicMock()
    adapter = FinTSBalanceAdapter(creds)

    result = BalanceResult(
        booked=MT940Balance(
            amount=Decimal("1000.00"),
            currency="EUR",
            date=date(2024, 1, 10),
            status="C",
        ),
        pending=MT940Balance(
            amount=Decimal("50.00"),
            currency="EUR",
            date=date(2024, 1, 10),
            status="D",  # Debit (pending outflow)
        ),
        available=Decimal("950.00"),
        credit_line=Decimal("5000.00"),
    )

    snapshot = adapter._balance_from_operations("acct", result)

    # Booked balance
    assert snapshot.booked.amount == Decimal("1000.00")
    assert snapshot.booked.currency == "EUR"

    # Pending balance (debit should be negative)
    assert snapshot.pending is not None
    assert snapshot.pending.amount == Decimal("-50.00")
    assert snapshot.pending.currency == "EUR"

    # Available balance
    assert snapshot.available is not None
    assert snapshot.available.amount == Decimal("950.00")
    assert snapshot.available.currency == "EUR"

    # Credit limit
    assert snapshot.credit_limit is not None
    assert snapshot.credit_limit.amount == Decimal("5000.00")
    assert snapshot.credit_limit.currency == "EUR"


def test_balance_adapter_debit_balance_is_negative():
    """Test that debit balances are converted to negative amounts."""
    from geldstrom.infrastructure.fints.adapters.balances import FinTSBalanceAdapter
    from geldstrom.infrastructure.fints.operations import BalanceResult, MT940Balance

    creds = MagicMock()
    adapter = FinTSBalanceAdapter(creds)

    result = BalanceResult(
        booked=MT940Balance(
            amount=Decimal("100.00"),
            currency="EUR",
            date=date(2024, 1, 5),
            status="D",  # Debit (negative balance)
        ),
    )

    snapshot = adapter._balance_from_operations("acct", result)

    assert snapshot.booked.amount == Decimal("-100.00")


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
                "applicant_iban": "DE89370400440532013000",
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
    assert feed.entries[0].counterpart_name == "Alice"
    assert feed.entries[0].counterpart_iban == "DE89370400440532013000"
    assert feed.entries[1].amount == Decimal("-2")
    assert feed.entries[1].counterpart_name == "Bob"
    assert feed.entries[1].counterpart_iban is None


def test_transactions_adapter_has_more_propagation_mt940():
    """Test that has_more flag is propagated from MT940 results."""
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
            }
        ),
    ]

    # Test with has_more=False
    feed = adapter._transactions_from_mt940("acct", txns, has_more=False)
    assert feed.has_more is False

    # Test with has_more=True
    feed = adapter._transactions_from_mt940("acct", txns, has_more=True)
    assert feed.has_more is True


def test_transactions_adapter_has_more_propagation_camt():
    """Test that has_more flag is propagated from CAMT results."""
    from geldstrom.infrastructure.fints.adapters.transactions import (
        FinTSTransactionHistory,
    )

    creds = MagicMock()
    adapter = FinTSTransactionHistory(creds)

    document = _build_camt_document(
        amount="100.00",
        indicator="CRDT",
        entry_id="TEST",
        addtl_info="Test",
        remittance="Test",
        counterpart_name="Test",
        counterpart_iban="DE001234",
    )

    # Test with has_more=False
    feed = adapter._transactions_from_camt("acct", [document], [], has_more=False)
    assert feed.has_more is False

    # Test with has_more=True
    feed = adapter._transactions_from_camt("acct", [document], [], has_more=True)
    assert feed.has_more is True


@pytest.mark.parametrize(
    "name_structure,expected_name,description",
    [
        # Standard structure: <Dbtr><Nm>...</Nm></Dbtr>
        (
            "<Dbtr><Nm>Direct Name GmbH</Nm></Dbtr>",
            "Direct Name GmbH",
            "Direct Nm under Dbtr (standard)",
        ),
        # Party wrapper: <Dbtr><Pty><Nm>...</Nm></Pty></Dbtr> (Triodos style)
        (
            "<Dbtr><Pty><Nm>Party Wrapper Name</Nm></Pty></Dbtr>",
            "Party Wrapper Name",
            "Nm under Pty wrapper (Triodos)",
        ),
        # Postal address: <Dbtr><PstlAdr><Nm>...</Nm></PstlAdr></Dbtr>
        (
            "<Dbtr><PstlAdr><Nm>Postal Address Name</Nm></PstlAdr></Dbtr>",
            "Postal Address Name",
            "Nm under PstlAdr",
        ),
        # Deeply nested structure
        (
            "<Dbtr><Pty><PstlAdr><Nm>Deeply Nested Name</Nm></PstlAdr></Pty></Dbtr>",
            "Deeply Nested Name",
            "Deeply nested Nm",
        ),
        # Ultimate party fallback: <UltmtDbtr><Nm>...</Nm></UltmtDbtr>
        (
            "<UltmtDbtr><Nm>Ultimate Party Name</Nm></UltmtDbtr>",
            "Ultimate Party Name",
            "Nm under UltmtDbtr fallback",
        ),
        # Ultimate party with wrapper
        (
            "<UltmtDbtr><Pty><Nm>Ultimate Pty Name</Nm></Pty></UltmtDbtr>",
            "Ultimate Pty Name",
            "Nm under UltmtDbtr/Pty",
        ),
        # Direct party takes precedence over ultimate
        (
            "<Dbtr><Nm>Direct Takes Priority</Nm></Dbtr>"
            "<UltmtDbtr><Nm>Ultimate Ignored</Nm></UltmtDbtr>",
            "Direct Takes Priority",
            "Direct Dbtr preferred over UltmtDbtr",
        ),
        # Empty direct, falls back to ultimate
        (
            "<Dbtr><Nm>   </Nm></Dbtr>"
            "<UltmtDbtr><Nm>Fallback to Ultimate</Nm></UltmtDbtr>",
            "Fallback to Ultimate",
            "Empty Dbtr/Nm falls back to UltmtDbtr",
        ),
        # No name elements at all
        (
            "<Dbtr><Id>12345</Id></Dbtr>",
            None,
            "No Nm element anywhere",
        ),
        # Empty Dbtr element
        (
            "<Dbtr></Dbtr>",
            None,
            "Empty Dbtr element",
        ),
    ],
)
def test_transactions_adapter_camt_counterpart_name_structures(
    name_structure: str,
    expected_name: str | None,
    description: str,
):
    """Test CAMT parsing handles various XML structures for counterpart name.

    Banks use different structures for counterparty information. The parser
    should find <Nm> elements regardless of intermediate wrapper elements.
    """
    from geldstrom.infrastructure.fints.adapters.transactions import (
        FinTSTransactionHistory,
    )

    creds = MagicMock()
    adapter = FinTSTransactionHistory(creds)

    document = _build_camt_document_with_custom_party_structure(
        amount="100.00",
        indicator="CRDT",
        entry_id="TEST123",
        party_structure=name_structure,
        counterpart_iban="DE89370400440532013000",
    )

    feed = adapter._transactions_from_camt("acct", [document], [])

    assert len(feed.entries) == 1, f"Failed for: {description}"
    entry = feed.entries[0]
    assert entry.counterpart_name == expected_name, f"Failed for: {description}"


@pytest.mark.parametrize(
    "name_structure,expected_name,description",
    [
        # Standard: <Cdtr><Nm>...</Nm></Cdtr>
        (
            "<Cdtr><Nm>Creditor Direct</Nm></Cdtr>",
            "Creditor Direct",
            "Direct Nm under Cdtr",
        ),
        # Party wrapper for creditor
        (
            "<Cdtr><Pty><Nm>Creditor Pty Name</Nm></Pty></Cdtr>",
            "Creditor Pty Name",
            "Nm under Cdtr/Pty",
        ),
        # Ultimate creditor
        (
            "<UltmtCdtr><Nm>Ultimate Creditor</Nm></UltmtCdtr>",
            "Ultimate Creditor",
            "Nm under UltmtCdtr",
        ),
    ],
)
def test_transactions_adapter_camt_creditor_name_structures(
    name_structure: str,
    expected_name: str | None,
    description: str,
):
    """Test CAMT parsing for DBIT transactions (creditor as counterpart)."""
    from geldstrom.infrastructure.fints.adapters.transactions import (
        FinTSTransactionHistory,
    )

    creds = MagicMock()
    adapter = FinTSTransactionHistory(creds)

    document = _build_camt_document_with_custom_party_structure(
        amount="50.00",
        indicator="DBIT",  # Debit = we're paying, so counterpart is Cdtr
        entry_id="DBIT123",
        party_structure=name_structure,
        counterpart_iban="NL91ABNA0417164300",
    )

    feed = adapter._transactions_from_camt("acct", [document], [])

    assert len(feed.entries) == 1, f"Failed for: {description}"
    entry = feed.entries[0]
    assert entry.counterpart_name == expected_name, f"Failed for: {description}"
    assert entry.amount < 0, "DBIT should be negative"


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
""".encode()


def _build_camt_document_with_ultimate_party(
    amount: str,
    indicator: str,
    entry_id: str,
    addtl_info: str,
    remittance: str,
    ultimate_party_name: str,
    counterpart_iban: str,
    booking_date: str = "2025-01-10",
    value_date: str = "2025-01-09",
) -> bytes:
    """Build CAMT document where name is only in UltmtDbtr (not Dbtr/Nm).

    This simulates banks that put counterparty info in
    Ultimate party fields instead of direct party fields.
    """
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
              <UltmtDbtr>
                <Nm>{ultimate_party_name}</Nm>
              </UltmtDbtr>
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
""".encode()


def _build_camt_document_with_pty_wrapper(
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
    """Build CAMT document with Pty wrapper around counterparty name.

    Triodos uses <Cdtr><Pty><Nm>...</Nm></Pty></Cdtr> structure
    instead of <Cdtr><Nm>...</Nm></Cdtr>.
    """
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
              <Cdtr>
                <Pty>
                  <Nm>{counterpart_name}</Nm>
                </Pty>
              </Cdtr>
              <CdtrAcct>
                <Id>
                  <IBAN>{counterpart_iban}</IBAN>
                </Id>
              </CdtrAcct>
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
""".encode()


def _build_camt_document_with_custom_party_structure(
    amount: str,
    indicator: str,
    entry_id: str,
    party_structure: str,
    counterpart_iban: str,
    booking_date: str = "2025-01-10",
    value_date: str = "2025-01-09",
) -> bytes:
    """Build CAMT document with custom party structure for testing.

    Allows testing various XML structures for counterparty information.
    The party_structure should contain the relevant party elements
    (e.g., <Dbtr><Nm>...</Nm></Dbtr>).

    For CRDT: counterpart is Dbtr (debtor paying us)
    For DBIT: counterpart is Cdtr (creditor we're paying)
    """
    # Determine account tag based on indicator
    acct_tag = "DbtrAcct" if indicator == "CRDT" else "CdtrAcct"

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<Document xmlns='urn:iso:std:iso:20022:tech:xsd:camt.052.001.08'>
  <BkToCstmrAcctRpt>
    <Rpt>
      <Ntry>
        <Amt Ccy='EUR'>{amount}</Amt>
        <CdtDbtInd>{indicator}</CdtDbtInd>
        <BookgDt><Dt>{booking_date}</Dt></BookgDt>
        <ValDt><Dt>{value_date}</Dt></ValDt>
        <AddtlNtryInf>Test transaction</AddtlNtryInf>
        <NtryDtls>
          <TxDtls>
            <Refs>
              <EndToEndId>{entry_id}</EndToEndId>
            </Refs>
            <RltdPties>
              {party_structure}
              <{acct_tag}>
                <Id>
                  <IBAN>{counterpart_iban}</IBAN>
                </Id>
              </{acct_tag}>
            </RltdPties>
            <RmtInf>
              <Ustrd>Test remittance</Ustrd>
            </RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
    </Rpt>
  </BkToCstmrAcctRpt>
</Document>
""".encode()
