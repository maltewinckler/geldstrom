"""Unit tests for fints.infrastructure.fints.protocol.formals.

Tests cover:
- Enums
- Identifier DEGs (BankIdentifier, AccountIdentifier, etc.)
- Amount DEGs (Amount, Balance)
- Security DEGs
- Response DEGs
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from geldstrom.infrastructure.fints.protocol.formals import (
    COUNTRY_ALPHA_TO_NUMERIC,
    COUNTRY_NUMERIC_TO_ALPHA,
    AccountIdentifier,
    AccountInternational,
    # Amounts
    Amount,
    Balance,
    # Identifiers
    BankIdentifier,
    # Enums
    CreditDebit,
    DateTimeType,
    IdentifiedRole,
    KeyName,
    KeyType,
    ReferenceMessage,
    # Responses
    Response,
    SecurityDateTime,
    SecurityIdentificationDetails,
    SecurityMethod,
    # Security
    SecurityProfile,
    Timestamp,
    UserDefinedSignature,
)

# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for FinTS enums."""

    def test_security_method_values(self):
        """SecurityMethod enum has correct values."""
        assert SecurityMethod.PIN == "PIN"
        assert SecurityMethod.RDH == "RDH"
        assert SecurityMethod.DDV == "DDV"

    def test_credit_debit_values(self):
        """CreditDebit enum has correct values."""
        assert CreditDebit.CREDIT == "C"
        assert CreditDebit.DEBIT == "D"

    def test_identified_role_values(self):
        """IdentifiedRole enum has correct values."""
        assert IdentifiedRole.MS == "1"
        assert IdentifiedRole.MR == "2"

    def test_key_type_values(self):
        """KeyType enum has correct values."""
        assert KeyType.D == "D"
        assert KeyType.S == "S"
        assert KeyType.V == "V"


# =============================================================================
# Identifier Tests
# =============================================================================


class TestBankIdentifier:
    """Tests for BankIdentifier DEG."""

    def test_creation(self):
        """Create BankIdentifier with values."""
        bank = BankIdentifier(country_identifier="280", bank_code="12345678")
        assert bank.country_identifier == "280"
        assert bank.bank_code == "12345678"

    def test_from_wire_list(self):
        """Parse BankIdentifier from wire list."""
        bank = BankIdentifier.from_wire_list(["280", "12345678"])
        assert bank.country_identifier == "280"
        assert bank.bank_code == "12345678"

    def test_to_wire_list(self):
        """Export BankIdentifier to wire list."""
        bank = BankIdentifier(country_identifier="280", bank_code="12345678")
        wire = bank.to_wire_list()
        assert wire == ["280", "12345678"]

    def test_country_alpha_property(self):
        """country_alpha returns ISO alpha-2 code."""
        bank = BankIdentifier(country_identifier="280", bank_code="12345678")
        assert bank.country_alpha == "DE"

    def test_equality(self):
        """BankIdentifier equality comparison."""
        bank1 = BankIdentifier(country_identifier="280", bank_code="12345678")
        bank2 = BankIdentifier(country_identifier="280", bank_code="12345678")
        bank3 = BankIdentifier(country_identifier="280", bank_code="87654321")

        assert bank1 == bank2
        assert bank1 != bank3

    def test_hashable(self):
        """BankIdentifier is hashable."""
        bank = BankIdentifier(country_identifier="280", bank_code="12345678")
        # Should not raise
        hash(bank)
        # Can be used in sets
        {bank}

    def test_class_country_mappings(self):
        """Class-level country mappings are accessible."""
        assert BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC["DE"] == "280"
        assert BankIdentifier.COUNTRY_NUMERIC_TO_ALPHA["280"] == "DE"


class TestCountryMappings:
    """Tests for country code mappings."""

    def test_common_countries(self):
        """Common country codes are mapped correctly."""
        assert COUNTRY_ALPHA_TO_NUMERIC["DE"] == "280"
        assert COUNTRY_ALPHA_TO_NUMERIC["AT"] == "040"
        assert COUNTRY_ALPHA_TO_NUMERIC["CH"] == "756"
        assert COUNTRY_ALPHA_TO_NUMERIC["FR"] == "250"

    def test_reverse_mapping(self):
        """Reverse mapping is complete."""
        for alpha, numeric in COUNTRY_ALPHA_TO_NUMERIC.items():
            assert COUNTRY_NUMERIC_TO_ALPHA[numeric] == alpha

    def test_alternative_german_code(self):
        """Alternative German code 276 maps to DE."""
        assert COUNTRY_NUMERIC_TO_ALPHA["276"] == "DE"


class TestAccountIdentifier:
    """Tests for AccountIdentifier DEG."""

    def test_creation(self):
        """Create AccountIdentifier with values."""
        bank = BankIdentifier(country_identifier="280", bank_code="12345678")
        account = AccountIdentifier(
            account_number="1234567890",
            subaccount_number="00",
            bank_identifier=bank,
        )
        assert account.account_number == "1234567890"
        assert account.subaccount_number == "00"
        assert account.bank_identifier.bank_code == "12345678"

    def test_from_wire_list(self):
        """Parse AccountIdentifier from wire list."""
        account = AccountIdentifier.from_wire_list(
            [
                "1234567890",
                "00",
                ["280", "12345678"],
            ]
        )
        assert account.account_number == "1234567890"
        assert account.subaccount_number == "00"
        assert account.bank_identifier.bank_code == "12345678"


class TestAccountInternational:
    """Tests for AccountInternational (KTI1) DEG."""

    def test_creation_with_iban(self):
        """Create AccountInternational with IBAN."""
        account = AccountInternational(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )
        assert account.iban == "DE89370400440532013000"
        assert account.bic == "COBADEFFXXX"
        assert account.account_number is None

    def test_all_fields_optional(self):
        """All fields can be None."""
        account = AccountInternational()
        assert account.iban is None
        assert account.bic is None
        assert account.account_number is None


# =============================================================================
# Amount Tests
# =============================================================================


class TestAmount:
    """Tests for Amount DEG."""

    def test_creation(self):
        """Create Amount with values."""
        amount = Amount(amount=Decimal("1234.56"), currency="EUR")
        assert amount.amount == Decimal("1234.56")
        assert amount.currency == "EUR"

    def test_from_wire_list(self):
        """Parse Amount from wire list."""
        amount = Amount.from_wire_list(["1234,56", "EUR"])
        assert amount.amount == Decimal("1234.56")
        assert amount.currency == "EUR"

    def test_to_wire_list(self):
        """Export Amount to wire list."""
        amount = Amount(amount=Decimal("1234.56"), currency="EUR")
        wire = amount.to_wire_list()
        assert wire[0] == Decimal("1234.56")
        assert wire[1] == "EUR"

    def test_str(self):
        """String representation."""
        amount = Amount(amount=Decimal("1234.56"), currency="EUR")
        assert str(amount) == "1234.56 EUR"


class TestBalance:
    """Tests for Balance DEG."""

    def test_creation_credit(self):
        """Create credit Balance."""
        balance = Balance(
            credit_debit=CreditDebit.CREDIT,
            amount=Amount(amount=Decimal("1000.00"), currency="EUR"),
            date=date(2023, 12, 25),
        )
        assert balance.credit_debit == CreditDebit.CREDIT
        assert balance.amount.amount == Decimal("1000.00")
        assert balance.date == date(2023, 12, 25)

    def test_creation_debit(self):
        """Create debit Balance."""
        balance = Balance(
            credit_debit=CreditDebit.DEBIT,
            amount=Amount(amount=Decimal("500.00"), currency="EUR"),
            date=date(2023, 12, 25),
        )
        assert balance.credit_debit == CreditDebit.DEBIT
        assert balance.signed_amount == Decimal("-500.00")

    def test_signed_amount_credit(self):
        """signed_amount is positive for credit."""
        balance = Balance(
            credit_debit=CreditDebit.CREDIT,
            amount=Amount(amount=Decimal("1000.00"), currency="EUR"),
            date=date(2023, 12, 25),
        )
        assert balance.signed_amount == Decimal("1000.00")

    def test_signed_amount_debit(self):
        """signed_amount is negative for debit."""
        balance = Balance(
            credit_debit=CreditDebit.DEBIT,
            amount=Amount(amount=Decimal("500.00"), currency="EUR"),
            date=date(2023, 12, 25),
        )
        assert balance.signed_amount == Decimal("-500.00")

    def test_currency_property(self):
        """currency property returns nested currency."""
        balance = Balance(
            credit_debit=CreditDebit.CREDIT,
            amount=Amount(amount=Decimal("1000.00"), currency="EUR"),
            date=date(2023, 12, 25),
        )
        assert balance.currency == "EUR"

    def test_from_wire_list(self):
        """Parse Balance from wire list."""
        balance = Balance.from_wire_list(
            [
                "C",
                ["1000,00", "EUR"],
                "20231225",
            ]
        )
        assert balance.credit_debit == CreditDebit.CREDIT
        assert balance.amount.amount == Decimal("1000.00")
        assert balance.date == date(2023, 12, 25)

    def test_with_time(self):
        """Balance with optional time."""
        balance = Balance(
            credit_debit=CreditDebit.CREDIT,
            amount=Amount(amount=Decimal("1000.00"), currency="EUR"),
            date=date(2023, 12, 25),
            time=time(14, 30, 0),
        )
        assert balance.time == time(14, 30, 0)


class TestTimestamp:
    """Tests for Timestamp DEG."""

    def test_creation(self):
        """Create Timestamp with date only."""
        ts = Timestamp(date=date(2023, 12, 25))
        assert ts.date == date(2023, 12, 25)
        assert ts.time is None

    def test_with_time(self):
        """Create Timestamp with date and time."""
        ts = Timestamp(date=date(2023, 12, 25), time=time(14, 30, 0))
        assert ts.date == date(2023, 12, 25)
        assert ts.time == time(14, 30, 0)


# =============================================================================
# Security Tests
# =============================================================================


class TestSecurityProfile:
    """Tests for SecurityProfile DEG."""

    def test_creation(self):
        """Create SecurityProfile."""
        profile = SecurityProfile(
            security_method=SecurityMethod.PIN,
            security_method_version=1,
        )
        assert profile.security_method == SecurityMethod.PIN
        assert profile.security_method_version == 1

    def test_from_wire_list(self):
        """Parse SecurityProfile from wire list."""
        profile = SecurityProfile.from_wire_list(["PIN", "1"])
        assert profile.security_method == SecurityMethod.PIN
        assert profile.security_method_version == 1


class TestSecurityIdentificationDetails:
    """Tests for SecurityIdentificationDetails DEG."""

    def test_creation(self):
        """Create SecurityIdentificationDetails."""
        details = SecurityIdentificationDetails(
            identified_role=IdentifiedRole.MS,
            identifier="0",
        )
        assert details.identified_role == IdentifiedRole.MS
        assert details.identifier == "0"
        assert details.cid is None


class TestSecurityDateTime:
    """Tests for SecurityDateTime DEG."""

    def test_creation(self):
        """Create SecurityDateTime."""
        sdt = SecurityDateTime(
            date_time_type=DateTimeType.STS,
            date=date(2023, 12, 25),
            time=time(14, 30, 0),
        )
        assert sdt.date_time_type == DateTimeType.STS
        assert sdt.date == date(2023, 12, 25)
        assert sdt.time == time(14, 30, 0)


class TestKeyName:
    """Tests for KeyName DEG."""

    def test_creation(self):
        """Create KeyName."""
        key = KeyName(
            bank_identifier=BankIdentifier(
                country_identifier="280", bank_code="12345678"
            ),
            user_id="testuser",
            key_type=KeyType.S,
            key_number=0,
            key_version=0,
        )
        assert key.bank_identifier.bank_code == "12345678"
        assert key.user_id == "testuser"
        assert key.key_type == KeyType.S
        assert key.key_number == 0


class TestUserDefinedSignature:
    """Tests for UserDefinedSignature DEG."""

    def test_with_pin_only(self):
        """Create with PIN only."""
        sig = UserDefinedSignature(pin="12345")
        assert sig.pin == "12345"
        assert sig.tan is None

    def test_with_pin_and_tan(self):
        """Create with PIN and TAN."""
        sig = UserDefinedSignature(pin="12345", tan="654321")
        assert sig.pin == "12345"
        assert sig.tan == "654321"

    def test_repr_masks_credentials(self):
        """Ensure __repr__ masks PIN and TAN to prevent credential leakage."""
        sig = UserDefinedSignature(pin="supersecret123", tan="tan456")
        repr_str = repr(sig)

        # PIN and TAN should not appear in repr
        assert "supersecret123" not in repr_str
        assert "tan456" not in repr_str
        # Should show masked values
        assert "***" in repr_str

    def test_str_masks_credentials(self):
        """Ensure __str__ masks PIN and TAN to prevent credential leakage."""
        sig = UserDefinedSignature(pin="mysecretpin", tan=None)
        str_repr = str(sig)

        # PIN should not appear in str
        assert "mysecretpin" not in str_repr
        assert "***" in str_repr


# =============================================================================
# Response Tests
# =============================================================================


class TestResponse:
    """Tests for Response DEG."""

    def test_success_response(self):
        """Create success response."""
        resp = Response(
            code="0010",
            reference_element="3",
            text="Auftrag entgegengenommen",
        )
        assert resp.code == "0010"
        assert resp.is_success is True
        assert resp.is_warning is False
        assert resp.is_error is False

    def test_warning_response(self):
        """Create warning response."""
        resp = Response(
            code="3040",
            reference_element="5",
            text="Es liegen weitere Daten vor",
        )
        assert resp.is_success is False
        assert resp.is_warning is True
        assert resp.is_error is False

    def test_error_response(self):
        """Create error response."""
        resp = Response(
            code="9050",
            reference_element="0",
            text="Teilweise fehlerhaft",
        )
        assert resp.is_success is False
        assert resp.is_warning is False
        assert resp.is_error is True

    def test_str_representation(self):
        """String representation includes code and text."""
        resp = Response(
            code="0010",
            reference_element="3",
            text="Auftrag entgegengenommen",
        )
        assert str(resp) == "0010: Auftrag entgegengenommen"

    def test_from_wire_list(self):
        """Parse Response from wire list."""
        resp = Response.from_wire_list(["0010", "3", "OK"])
        assert resp.code == "0010"
        assert resp.reference_element == "3"
        assert resp.text == "OK"


class TestReferenceMessage:
    """Tests for ReferenceMessage DEG."""

    def test_creation(self):
        """Create ReferenceMessage."""
        ref = ReferenceMessage(dialog_id="ABC123", message_number=1)
        assert ref.dialog_id == "ABC123"
        assert ref.message_number == 1
