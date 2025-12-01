"""Unit tests for fints.infrastructure.fints.protocol.segments.

Tests cover:
- Balance segments (HKSAL, HISAL)
- Account segments (HKSPA, HISPA)
- Transaction segments (HKKAZ, HIKAZ, HKCAZ, HICAZ)
- Statement segments (HKEKA, HIEKA, HKKAU, HIKAU)
- Segment version registries
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest

from geldstrom.infrastructure.fints.protocol.base import SegmentHeader
from geldstrom.infrastructure.fints.protocol.formals import (
    AccountIdentifier,
    AccountInternational,
    AccountInternationalSEPA,
    Amount,
    Balance,
    BalanceSimple,
    BankIdentifier,
    BookedCamtStatements,
    Confirmation,
    CreditDebit,
    StatementFormat,
    SupportedMessageTypes,
    Timestamp,
)
from geldstrom.infrastructure.fints.protocol.segments import (
    # Balance segments
    HKSAL5,
    HKSAL6,
    HKSAL7,
    HISAL5,
    HISAL6,
    HISAL7,
    HKSAL_VERSIONS,
    HISAL_VERSIONS,
    # Account segments
    HKSPA1,
    HISPA1,
    # Transaction segments
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    HKKAZ_VERSIONS,
    HIKAZ5,
    HIKAZ6,
    HIKAZ7,
    HIKAZ_VERSIONS,
    HKCAZ1,
    HKCAZ_VERSIONS,
    HICAZ1,
    HICAZ_VERSIONS,
    # Statement segments
    HKEKA3,
    HKEKA4,
    HKEKA5,
    HKEKA_VERSIONS,
    HIEKA3,
    HIEKA4,
    HIEKA5,
    HIEKA_VERSIONS,
    HKKAU1,
    HKKAU2,
    HKKAU_VERSIONS,
    HIKAU1,
    HIKAU2,
    HIKAU_VERSIONS,
    ReportPeriod,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_header() -> SegmentHeader:
    """Create sample segment header."""
    return SegmentHeader(type="HISAL", number=5, version=6)


@pytest.fixture
def sample_bank_identifier() -> BankIdentifier:
    """Create sample bank identifier."""
    return BankIdentifier(country_identifier="280", bank_code="12345678")


@pytest.fixture
def sample_account(sample_bank_identifier) -> AccountIdentifier:
    """Create sample account identifier."""
    return AccountIdentifier(
        account_number="1234567890",
        subaccount_number="00",
        bank_identifier=sample_bank_identifier,
    )


@pytest.fixture
def sample_amount() -> Amount:
    """Create sample amount."""
    return Amount(amount=Decimal("1234.56"), currency="EUR")


@pytest.fixture
def sample_balance(sample_amount) -> Balance:
    """Create sample balance."""
    return Balance(
        credit_debit=CreditDebit.CREDIT,
        amount=sample_amount,
        date=date(2023, 12, 25),
    )


@pytest.fixture
def sample_balance_simple() -> BalanceSimple:
    """Create sample simple balance."""
    return BalanceSimple(
        credit_debit=CreditDebit.CREDIT,
        amount=Decimal("1234.56"),
        currency="EUR",
        date=date(2023, 12, 25),
    )


# =============================================================================
# HKSAL Tests
# =============================================================================


class TestHKSAL:
    """Tests for HKSAL (balance request) segments."""

    def test_hksal5_creation(self, sample_header, sample_account):
        """Create HKSAL5 segment."""
        sample_header.type = "HKSAL"
        sample_header.version = 5

        segment = HKSAL5(
            header=sample_header,
            account=sample_account,
            all_accounts=False,
        )
        assert segment.SEGMENT_TYPE == "HKSAL"
        assert segment.SEGMENT_VERSION == 5
        assert segment.account.account_number == "1234567890"
        assert segment.all_accounts is False

    def test_hksal6_creation(self, sample_header, sample_account):
        """Create HKSAL6 segment."""
        sample_header.type = "HKSAL"
        sample_header.version = 6

        segment = HKSAL6(
            header=sample_header,
            account=sample_account,
            all_accounts=True,
        )
        assert segment.SEGMENT_VERSION == 6
        assert segment.all_accounts is True

    def test_hksal7_with_international_account(self, sample_header):
        """Create HKSAL7 with international account."""
        sample_header.type = "HKSAL"
        sample_header.version = 7

        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )

        segment = HKSAL7(
            header=sample_header,
            account=account,
            all_accounts=False,
        )
        assert segment.SEGMENT_VERSION == 7
        assert segment.account.iban == "DE89370400440532013000"

    def test_hksal_optional_fields(self, sample_header, sample_account):
        """HKSAL optional fields default to None."""
        sample_header.type = "HKSAL"
        sample_header.version = 6

        segment = HKSAL6(
            header=sample_header,
            account=sample_account,
            all_accounts=False,
        )
        assert segment.max_number_responses is None
        assert segment.touchdown_point is None

    def test_hksal_with_pagination(self, sample_header, sample_account):
        """HKSAL with pagination parameters."""
        sample_header.type = "HKSAL"
        sample_header.version = 6

        segment = HKSAL6(
            header=sample_header,
            account=sample_account,
            all_accounts=False,
            max_number_responses=100,
            touchdown_point="ABC123",
        )
        assert segment.max_number_responses == 100
        assert segment.touchdown_point == "ABC123"

    def test_hksal_version_registry(self):
        """HKSAL version registry contains all versions."""
        assert 5 in HKSAL_VERSIONS
        assert 6 in HKSAL_VERSIONS
        assert 7 in HKSAL_VERSIONS
        assert HKSAL_VERSIONS[5] == HKSAL5
        assert HKSAL_VERSIONS[6] == HKSAL6
        assert HKSAL_VERSIONS[7] == HKSAL7


# =============================================================================
# HISAL Tests
# =============================================================================


class TestHISAL:
    """Tests for HISAL (balance response) segments."""

    def test_hisal5_creation(self, sample_header, sample_account, sample_balance_simple):
        """Create HISAL5 segment."""
        sample_header.type = "HISAL"
        sample_header.version = 5

        segment = HISAL5(
            header=sample_header,
            account=sample_account,
            account_product="Girokonto",
            currency="EUR",
            balance_booked=sample_balance_simple,
        )
        assert segment.SEGMENT_TYPE == "HISAL"
        assert segment.SEGMENT_VERSION == 5
        assert segment.account_product == "Girokonto"
        assert segment.balance_booked.signed_amount == Decimal("1234.56")

    def test_hisal6_creation(self, sample_header, sample_account, sample_balance):
        """Create HISAL6 segment."""
        sample_header.type = "HISAL"
        sample_header.version = 6

        segment = HISAL6(
            header=sample_header,
            account=sample_account,
            account_product="Girokonto Plus",
            currency="EUR",
            balance_booked=sample_balance,
        )
        assert segment.SEGMENT_VERSION == 6
        assert segment.balance_booked.credit_debit == CreditDebit.CREDIT

    def test_hisal7_creation(self, sample_header, sample_balance):
        """Create HISAL7 with international account."""
        sample_header.type = "HISAL"
        sample_header.version = 7

        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )

        segment = HISAL7(
            header=sample_header,
            account=account,
            account_product="International Account",
            currency="EUR",
            balance_booked=sample_balance,
        )
        assert segment.SEGMENT_VERSION == 7
        assert segment.account.iban == "DE89370400440532013000"

    def test_hisal6_with_all_optional_fields(self, sample_header, sample_account, sample_balance, sample_amount):
        """HISAL6 with all optional fields."""
        sample_header.type = "HISAL"
        sample_header.version = 6

        segment = HISAL6(
            header=sample_header,
            account=sample_account,
            account_product="Premium Account",
            currency="EUR",
            balance_booked=sample_balance,
            balance_pending=sample_balance,
            line_of_credit=sample_amount,
            available_amount=sample_amount,
            used_amount=sample_amount,
            overdraft=sample_amount,
            booking_timestamp=Timestamp(date=date(2023, 12, 25), time=time(14, 30)),
            date_due=date(2024, 1, 15),
        )
        assert segment.balance_pending is not None
        assert segment.line_of_credit.amount == Decimal("1234.56")
        assert segment.booking_timestamp.time == time(14, 30)
        assert segment.date_due == date(2024, 1, 15)

    def test_hisal_version_registry(self):
        """HISAL version registry contains all versions."""
        assert 5 in HISAL_VERSIONS
        assert 6 in HISAL_VERSIONS
        assert 7 in HISAL_VERSIONS
        assert HISAL_VERSIONS[5] == HISAL5
        assert HISAL_VERSIONS[6] == HISAL6
        assert HISAL_VERSIONS[7] == HISAL7


# =============================================================================
# HKSPA/HISPA Tests
# =============================================================================


class TestAccountSegments:
    """Tests for account segments (HKSPA, HISPA)."""

    def test_hkspa1_creation(self, sample_header):
        """Create HKSPA1 segment."""
        sample_header.type = "HKSPA"
        sample_header.version = 1

        segment = HKSPA1(header=sample_header)
        assert segment.SEGMENT_TYPE == "HKSPA"
        assert segment.SEGMENT_VERSION == 1
        assert segment.accounts is None

    def test_hkspa1_with_accounts(self, sample_header, sample_account):
        """Create HKSPA1 with account filter."""
        sample_header.type = "HKSPA"
        sample_header.version = 1

        segment = HKSPA1(
            header=sample_header,
            accounts=[sample_account],
        )
        assert len(segment.accounts) == 1
        assert segment.accounts[0].account_number == "1234567890"

    def test_hispa1_creation(self, sample_header):
        """Create HISPA1 segment."""
        sample_header.type = "HISPA"
        sample_header.version = 1

        segment = HISPA1(header=sample_header)
        assert segment.SEGMENT_TYPE == "HISPA"
        assert segment.SEGMENT_VERSION == 1
        assert segment.accounts is None

    def test_hispa1_with_accounts(self, sample_header, sample_bank_identifier):
        """Create HISPA1 with SEPA accounts."""
        sample_header.type = "HISPA"
        sample_header.version = 1

        sepa_account = AccountInternationalSEPA(
            is_sepa=True,
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            account_number="532013000",
            subaccount_number="00",
            bank_identifier=sample_bank_identifier,
        )

        segment = HISPA1(
            header=sample_header,
            accounts=[sepa_account],
        )
        assert len(segment.accounts) == 1
        assert segment.accounts[0].iban == "DE89370400440532013000"
        assert segment.accounts[0].is_sepa is True


# =============================================================================
# Segment ID Tests
# =============================================================================


class TestSegmentId:
    """Tests for segment ID functionality."""

    def test_segment_id_method(self):
        """segment_id() returns type + version."""
        assert HKSAL5.segment_id() == "HKSAL5"
        assert HKSAL6.segment_id() == "HKSAL6"
        assert HKSAL7.segment_id() == "HKSAL7"
        assert HISAL5.segment_id() == "HISAL5"
        assert HISAL6.segment_id() == "HISAL6"
        assert HISAL7.segment_id() == "HISAL7"
        assert HKSPA1.segment_id() == "HKSPA1"
        assert HISPA1.segment_id() == "HISPA1"
        assert HKKAZ5.segment_id() == "HKKAZ5"
        assert HIKAZ7.segment_id() == "HIKAZ7"
        assert HKCAZ1.segment_id() == "HKCAZ1"
        assert HICAZ1.segment_id() == "HICAZ1"
        assert HKEKA5.segment_id() == "HKEKA5"
        assert HIEKA5.segment_id() == "HIEKA5"
        assert HKKAU2.segment_id() == "HKKAU2"
        assert HIKAU2.segment_id() == "HIKAU2"


# =============================================================================
# Transaction Segment Tests
# =============================================================================


class TestHKKAZ:
    """Tests for HKKAZ (MT940 transaction request) segments."""

    def test_hkkaz5_creation(self, sample_header, sample_account):
        """Create HKKAZ5 segment."""
        sample_header.type = "HKKAZ"
        sample_header.version = 5

        segment = HKKAZ5(
            header=sample_header,
            account=sample_account,
            all_accounts=False,
        )
        assert segment.SEGMENT_TYPE == "HKKAZ"
        assert segment.SEGMENT_VERSION == 5
        assert segment.all_accounts is False

    def test_hkkaz7_with_dates(self, sample_header):
        """Create HKKAZ7 with date range."""
        sample_header.type = "HKKAZ"
        sample_header.version = 7

        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )

        segment = HKKAZ7(
            header=sample_header,
            account=account,
            all_accounts=False,
            date_start=date(2023, 1, 1),
            date_end=date(2023, 12, 31),
        )
        assert segment.date_start == date(2023, 1, 1)
        assert segment.date_end == date(2023, 12, 31)

    def test_hkkaz_version_registry(self):
        """HKKAZ version registry contains all versions."""
        assert 5 in HKKAZ_VERSIONS
        assert 6 in HKKAZ_VERSIONS
        assert 7 in HKKAZ_VERSIONS


class TestHIKAZ:
    """Tests for HIKAZ (MT940 transaction response) segments."""

    def test_hikaz5_creation(self, sample_header):
        """Create HIKAZ5 segment."""
        sample_header.type = "HIKAZ"
        sample_header.version = 5

        segment = HIKAZ5(
            header=sample_header,
            statement_booked=b":20:STARTUMS\n:25:12345678/1234567890\n",
        )
        assert segment.SEGMENT_TYPE == "HIKAZ"
        assert b"STARTUMS" in segment.statement_booked

    def test_hikaz_with_pending(self, sample_header):
        """Create HIKAZ with pending transactions."""
        sample_header.type = "HIKAZ"
        sample_header.version = 7

        segment = HIKAZ7(
            header=sample_header,
            statement_booked=b":20:STARTUMS\n",
            statement_pending=b":20:PENDUMS\n",
        )
        assert segment.statement_pending is not None

    def test_hikaz_version_registry(self):
        """HIKAZ version registry contains all versions."""
        assert 5 in HIKAZ_VERSIONS
        assert 6 in HIKAZ_VERSIONS
        assert 7 in HIKAZ_VERSIONS


class TestHKCAZ:
    """Tests for HKCAZ (CAMT transaction request) segments."""

    def test_hkcaz1_creation(self, sample_header):
        """Create HKCAZ1 segment."""
        sample_header.type = "HKCAZ"
        sample_header.version = 1

        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )

        camt_messages = SupportedMessageTypes(
            expected_type=["urn:iso:std:iso:20022:tech:xsd:camt.052.001.02"],
        )

        segment = HKCAZ1(
            header=sample_header,
            account=account,
            supported_camt_messages=camt_messages,
            all_accounts=False,
        )
        assert segment.SEGMENT_TYPE == "HKCAZ"
        assert segment.SEGMENT_VERSION == 1
        assert len(segment.supported_camt_messages.expected_type) == 1


class TestHICAZ:
    """Tests for HICAZ (CAMT transaction response) segments."""

    def test_hicaz1_creation(self, sample_header):
        """Create HICAZ1 segment."""
        sample_header.type = "HICAZ"
        sample_header.version = 1

        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )

        booked = BookedCamtStatements(
            camt_statements=[b"<Document>...</Document>"],
        )

        segment = HICAZ1(
            header=sample_header,
            account=account,
            camt_descriptor="urn:iso:std:iso:20022:tech:xsd:camt.052.001.02",
            statement_booked=booked,
        )
        assert segment.camt_descriptor.startswith("urn:iso")


# =============================================================================
# Statement Segment Tests
# =============================================================================


class TestHKEKA:
    """Tests for HKEKA (statement request) segments."""

    def test_hkeka3_creation(self, sample_header, sample_account):
        """Create HKEKA3 segment."""
        sample_header.type = "HKEKA"
        sample_header.version = 3

        segment = HKEKA3(
            header=sample_header,
            account=sample_account,
            statement_number=1,
            statement_year=2023,
        )
        assert segment.SEGMENT_TYPE == "HKEKA"
        assert segment.SEGMENT_VERSION == 3
        assert segment.statement_number == 1
        assert segment.statement_year == 2023

    def test_hkeka5_with_format(self, sample_header):
        """Create HKEKA5 with statement format."""
        sample_header.type = "HKEKA"
        sample_header.version = 5

        account = AccountInternational(
            iban="DE89370400440532013000",
        )

        segment = HKEKA5(
            header=sample_header,
            account=account,
            statement_format=StatementFormat.PDF,
            statement_number=12,
            statement_year=2023,
        )
        assert segment.statement_format == StatementFormat.PDF

    def test_hkeka_version_registry(self):
        """HKEKA version registry contains all versions."""
        assert 3 in HKEKA_VERSIONS
        assert 4 in HKEKA_VERSIONS
        assert 5 in HKEKA_VERSIONS


class TestHIEKA:
    """Tests for HIEKA (statement response) segments."""

    def test_hieka3_creation(self, sample_header):
        """Create HIEKA3 segment."""
        sample_header.type = "HIEKA"
        sample_header.version = 3

        report_period = ReportPeriod(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 31),
        )

        segment = HIEKA3(
            header=sample_header,
            statement_period=report_period,
            data=b"%PDF-1.4\n...",
        )
        assert segment.statement_period.start_date == date(2023, 1, 1)
        assert b"PDF" in segment.data

    def test_hieka5_with_metadata(self, sample_header):
        """Create HIEKA5 with all optional metadata."""
        sample_header.type = "HIEKA"
        sample_header.version = 5

        report_period = ReportPeriod(start_date=date(2023, 12, 1))

        segment = HIEKA5(
            header=sample_header,
            statement_format=StatementFormat.PDF,
            statement_period=report_period,
            data=b"...",
            date_created=date(2023, 12, 15),
            statement_year=2023,
            statement_number=12,
            account_iban="DE89370400440532013000",
            account_bic="COBADEFFXXX",
            statement_name_1="Kontoauszug Dezember",
        )
        assert segment.date_created == date(2023, 12, 15)
        assert segment.account_iban == "DE89370400440532013000"

    def test_hieka_version_registry(self):
        """HIEKA version registry contains all versions."""
        assert 3 in HIEKA_VERSIONS
        assert 4 in HIEKA_VERSIONS
        assert 5 in HIEKA_VERSIONS


class TestStatementOverview:
    """Tests for statement overview segments (HKKAU, HIKAU)."""

    def test_hkkau1_creation(self, sample_header, sample_account):
        """Create HKKAU1 segment."""
        sample_header.type = "HKKAU"
        sample_header.version = 1

        segment = HKKAU1(
            header=sample_header,
            account=sample_account,
        )
        assert segment.SEGMENT_TYPE == "HKKAU"

    def test_hikau1_creation(self, sample_header):
        """Create HIKAU1 segment."""
        sample_header.type = "HIKAU"
        sample_header.version = 1

        segment = HIKAU1(
            header=sample_header,
            statement_number=12,
            confirmation=Confirmation.NOT_REQUIRED,
            collection_possible=True,
            year=2023,
            date_created=date(2023, 12, 1),
        )
        assert segment.statement_number == 12
        assert segment.confirmation == Confirmation.NOT_REQUIRED
        assert segment.collection_possible is True

    def test_version_registries(self):
        """Version registries contain all versions."""
        assert 1 in HKKAU_VERSIONS
        assert 2 in HKKAU_VERSIONS
        assert 1 in HIKAU_VERSIONS
        assert 2 in HIKAU_VERSIONS

