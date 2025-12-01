"""Unit tests for optional segment migrations.

Tests cover:
- Transfer segments (transfer.py)
- Depot segments (depot.py)
- Journal segments (journal.py)
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest

from geldstrom.infrastructure.fints.protocol.segments import (
    # Transfer segments
    HKCCS1,
    HKIPZ1,
    HKCCM1,
    HKIPM1,
    HICCMS1,
    BatchTransferParameter,
    # Depot segments
    HKWPD5,
    HKWPD6,
    HIWPD5,
    HIWPD6,
    DepotAccount2,
    DepotAccount3,
    # Journal segments
    HKPRO3,
    HKPRO4,
    HIPRO3,
    HIPRO4,
    HIPROS3,
    HIPROS4,
)
from geldstrom.infrastructure.fints.protocol.formals import (
    AccountInternational,
    Amount,
    BankIdentifier,
    CreditDebit,
    ReferenceMessage,
    Response,
)
from geldstrom.infrastructure.fints.protocol.base import SegmentHeader


# =============================================================================
# Transfer Segment Tests
# =============================================================================


class TestTransferSegments:
    """Tests for SEPA transfer segments."""

    def test_hkccs1_creation(self):
        """Create single SEPA transfer segment."""
        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )
        seg = HKCCS1(
            header=SegmentHeader(type="HKCCS", version=1, number=3),
            account=account,
            sepa_descriptor="urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            sepa_pain_message=b"<XML>...</XML>",
        )
        assert seg.SEGMENT_TYPE == "HKCCS"
        assert seg.account.iban == "DE89370400440532013000"

    def test_hkipz1_creation(self):
        """Create instant SEPA transfer segment."""
        account = AccountInternational(
            iban="DE89370400440532013000",
        )
        seg = HKIPZ1(
            header=SegmentHeader(type="HKIPZ", version=1, number=3),
            account=account,
            sepa_descriptor="urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            sepa_pain_message=b"<XML>...</XML>",
        )
        assert seg.SEGMENT_TYPE == "HKIPZ"

    def test_hkccm1_creation(self):
        """Create batch SEPA transfer segment."""
        account = AccountInternational(
            iban="DE89370400440532013000",
        )
        sum_amount = Amount(
            amount=Decimal("1500.50"),
            currency="EUR",
            credit_debit=CreditDebit.DEBIT,
        )
        seg = HKCCM1(
            header=SegmentHeader(type="HKCCM", version=1, number=3),
            account=account,
            sum_amount=sum_amount,
            request_single_booking=False,
            sepa_descriptor="urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            sepa_pain_message=b"<XML>...</XML>",
        )
        assert seg.SEGMENT_TYPE == "HKCCM"
        assert seg.sum_amount.amount == Decimal("1500.50")

    def test_hkipm1_creation(self):
        """Create instant batch SEPA transfer segment."""
        account = AccountInternational(
            iban="DE89370400440532013000",
        )
        sum_amount = Amount(
            amount=Decimal("2500.00"),
            currency="EUR",
            credit_debit=CreditDebit.DEBIT,
        )
        seg = HKIPM1(
            header=SegmentHeader(type="HKIPM", version=1, number=3),
            account=account,
            sum_amount=sum_amount,
            request_single_booking=True,
            sepa_descriptor="urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            sepa_pain_message=b"<XML>...</XML>",
        )
        assert seg.request_single_booking is True

    def test_hiccms1_creation(self):
        """Create batch transfer parameter segment."""
        param = BatchTransferParameter(
            max_transfer_count=1000,
            sum_amount_required=True,
            single_booking_allowed=True,
        )
        seg = HICCMS1(
            header=SegmentHeader(type="HICCMS", version=1, number=5),
            max_number_tasks=1,
            min_number_signatures=1,
            security_class=0,
            parameter=param,
        )
        assert seg.SEGMENT_TYPE == "HICCMS"
        assert seg.parameter.max_transfer_count == 1000


# =============================================================================
# Depot Segment Tests
# =============================================================================


class TestDepotSegments:
    """Tests for depot/securities segments."""

    def test_hkwpd5_creation(self):
        """Create depot request segment v5."""
        account = DepotAccount2(
            account_number="1234567890",
            subaccount_number="00",
            country_identifier="280",
            bank_code="12345678",
        )
        seg = HKWPD5(
            header=SegmentHeader(type="HKWPD", version=5, number=3),
            account=account,
        )
        assert seg.SEGMENT_TYPE == "HKWPD"
        assert seg.account.account_number == "1234567890"

    def test_hkwpd5_with_options(self):
        """Create depot request segment v5 with options."""
        account = DepotAccount2(
            account_number="1234567890",
            subaccount_number="00",
            country_identifier="280",
            bank_code="12345678",
        )
        seg = HKWPD5(
            header=SegmentHeader(type="HKWPD", version=5, number=3),
            account=account,
            currency="EUR",
            quality=1,
            max_number_responses=100,
        )
        assert seg.currency == "EUR"
        assert seg.quality == 1

    def test_hkwpd6_creation(self):
        """Create depot request segment v6."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        account = DepotAccount3(
            account_number="1234567890",
            subaccount_number="00",
            bank_identifier=bank_id,
        )
        seg = HKWPD6(
            header=SegmentHeader(type="HKWPD", version=6, number=3),
            account=account,
        )
        assert seg.SEGMENT_VERSION == 6

    def test_hiwpd5_creation(self):
        """Create depot response segment v5."""
        seg = HIWPD5(
            header=SegmentHeader(type="HIWPD", version=5, number=4),
            holdings=b"MT535 data here",
        )
        assert seg.SEGMENT_TYPE == "HIWPD"
        assert b"MT535" in seg.holdings

    def test_hiwpd6_creation(self):
        """Create depot response segment v6."""
        seg = HIWPD6(
            header=SegmentHeader(type="HIWPD", version=6, number=4),
            holdings=b"<XML>Holdings data</XML>",
        )
        assert seg.SEGMENT_VERSION == 6


# =============================================================================
# Journal Segment Tests
# =============================================================================


class TestJournalSegments:
    """Tests for status protocol/journal segments."""

    def test_hkpro3_creation(self):
        """Create status protocol request v3."""
        seg = HKPRO3(
            header=SegmentHeader(type="HKPRO", version=3, number=3),
        )
        assert seg.SEGMENT_TYPE == "HKPRO"

    def test_hkpro3_with_date_range(self):
        """Create status protocol request v3 with date range."""
        seg = HKPRO3(
            header=SegmentHeader(type="HKPRO", version=3, number=3),
            date_start=date(2023, 1, 1),
            date_end=date(2023, 12, 31),
            max_number_responses=50,
        )
        assert seg.date_start == date(2023, 1, 1)
        assert seg.max_number_responses == 50

    def test_hkpro4_creation(self):
        """Create status protocol request v4."""
        seg = HKPRO4(
            header=SegmentHeader(type="HKPRO", version=4, number=3),
            date_start=date(2023, 6, 1),
        )
        assert seg.SEGMENT_VERSION == 4

    def test_hipro3_creation(self):
        """Create status protocol response v3."""
        ref = ReferenceMessage(dialog_id="123", message_number=1)
        responses = [
            Response(code="0010", reference_element="3", text="Verarbeitet"),
        ]
        seg = HIPRO3(
            header=SegmentHeader(type="HIPRO", version=3, number=4),
            reference_message=ref,
            date=date(2023, 12, 25),
            time=time(14, 30, 0),
            responses=responses,
        )
        assert seg.SEGMENT_TYPE == "HIPRO"
        assert seg.reference_message.dialog_id == "123"

    def test_hipro4_creation(self):
        """Create status protocol response v4."""
        ref = ReferenceMessage(dialog_id="456", message_number=2)
        responses = [
            Response(code="0010", reference_element="3", text="OK"),
            Response(code="3040", reference_element="4", text="Fortsetzung"),
        ]
        seg = HIPRO4(
            header=SegmentHeader(type="HIPRO", version=4, number=4),
            reference_message=ref,
            reference=5,
            date=date(2023, 12, 26),
            time=time(10, 15, 30),
            responses=responses,
        )
        assert seg.reference == 5
        assert len(seg.responses) == 2

    def test_hipros3_creation(self):
        """Create status protocol parameters v3."""
        seg = HIPROS3(
            header=SegmentHeader(type="HIPROS", version=3, number=5),
            max_number_tasks=1,
            min_number_signatures=0,
        )
        assert seg.SEGMENT_TYPE == "HIPROS"

    def test_hipros4_creation(self):
        """Create status protocol parameters v4."""
        seg = HIPROS4(
            header=SegmentHeader(type="HIPROS", version=4, number=5),
            max_number_tasks=1,
            min_number_signatures=1,
            security_class=0,
        )
        assert seg.SEGMENT_VERSION == 4

