"""Comprehensive unit tests for fints.protocol.types.

Tests cover:
- Individual validator functions
- Individual serializer functions
- Annotated types with Pydantic models
- Edge cases and error handling
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from geldstrom.infrastructure.fints.protocol.types import (
    # Validators
    parse_fints_amount,
    parse_fints_binary,
    parse_fints_bool,
    parse_fints_code,
    parse_fints_date,
    parse_fints_digits,
    parse_fints_numeric,
    parse_fints_text,
    parse_fints_time,
    # Serializers
    serialize_fints_amount,
    serialize_fints_bool,
    serialize_fints_date,
    serialize_fints_numeric,
    serialize_fints_time,
    # Annotated Types
    FinTSAlphanumeric,
    FinTSAmount,
    FinTSBinary,
    FinTSBool,
    FinTSCode,
    FinTSCountry,
    FinTSCurrency,
    FinTSDate,
    FinTSDigits,
    FinTSID,
    FinTSNumeric,
    FinTSText,
    FinTSTime,
)


# =============================================================================
# Date Validator Tests
# =============================================================================


class TestParseFintDate:
    """Tests for parse_fints_date validator."""

    def test_parse_valid_string(self):
        """Parse valid YYYYMMDD string."""
        assert parse_fints_date("20231225") == date(2023, 12, 25)
        assert parse_fints_date("20240101") == date(2024, 1, 1)
        assert parse_fints_date("19990101") == date(1999, 1, 1)

    def test_parse_date_passthrough(self):
        """Date objects pass through unchanged."""
        d = date(2023, 12, 25)
        assert parse_fints_date(d) is d

    def test_parse_with_whitespace(self):
        """Whitespace is stripped."""
        assert parse_fints_date("  20231225  ") == date(2023, 12, 25)

    def test_parse_invalid_format(self):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS date"):
            parse_fints_date("2023-12-25")

    def test_parse_too_short(self):
        """Too short string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS date"):
            parse_fints_date("2023122")

    def test_parse_invalid_date(self):
        """Invalid date components raise ValueError."""
        with pytest.raises(ValueError, match="Invalid date components"):
            parse_fints_date("20231332")  # Invalid month

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_date(None)

    def test_parse_non_numeric(self):
        """Non-numeric string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS date"):
            parse_fints_date("2023XXXX")


class TestSerializeFintDate:
    """Tests for serialize_fints_date serializer."""

    def test_serialize_date(self):
        """Serialize date to YYYYMMDD."""
        assert serialize_fints_date(date(2023, 12, 25)) == "20231225"
        assert serialize_fints_date(date(2024, 1, 1)) == "20240101"
        assert serialize_fints_date(date(1999, 1, 1)) == "19990101"


# =============================================================================
# Time Validator Tests
# =============================================================================


class TestParseFintTime:
    """Tests for parse_fints_time validator."""

    def test_parse_valid_string(self):
        """Parse valid HHMMSS string."""
        assert parse_fints_time("143022") == time(14, 30, 22)
        assert parse_fints_time("000000") == time(0, 0, 0)
        assert parse_fints_time("235959") == time(23, 59, 59)

    def test_parse_time_passthrough(self):
        """Time objects pass through unchanged."""
        t = time(14, 30, 22)
        assert parse_fints_time(t) is t

    def test_parse_with_whitespace(self):
        """Whitespace is stripped."""
        assert parse_fints_time("  143022  ") == time(14, 30, 22)

    def test_parse_invalid_format(self):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS time"):
            parse_fints_time("14:30:22")

    def test_parse_too_short(self):
        """Too short string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS time"):
            parse_fints_time("14302")

    def test_parse_invalid_time(self):
        """Invalid time components raise ValueError."""
        with pytest.raises(ValueError, match="Invalid time components"):
            parse_fints_time("256000")  # Invalid hour

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_time(None)


class TestSerializeFintTime:
    """Tests for serialize_fints_time serializer."""

    def test_serialize_time(self):
        """Serialize time to HHMMSS."""
        assert serialize_fints_time(time(14, 30, 22)) == "143022"
        assert serialize_fints_time(time(0, 0, 0)) == "000000"
        assert serialize_fints_time(time(23, 59, 59)) == "235959"


# =============================================================================
# Amount Validator Tests
# =============================================================================


class TestParseFintAmount:
    """Tests for parse_fints_amount validator."""

    def test_parse_german_decimal(self):
        """Parse German decimal format (comma separator)."""
        assert parse_fints_amount("1234,56") == Decimal("1234.56")
        assert parse_fints_amount("0,01") == Decimal("0.01")
        assert parse_fints_amount("1000000,99") == Decimal("1000000.99")

    def test_parse_integer_string(self):
        """Parse integer string."""
        assert parse_fints_amount("1234") == Decimal("1234")
        assert parse_fints_amount("0") == Decimal("0")

    def test_parse_decimal_passthrough(self):
        """Decimal objects pass through unchanged."""
        d = Decimal("1234.56")
        assert parse_fints_amount(d) == d

    def test_parse_int(self):
        """Integer converts to Decimal."""
        assert parse_fints_amount(1234) == Decimal("1234")

    def test_parse_float(self):
        """Float converts to Decimal (via string to avoid precision issues)."""
        result = parse_fints_amount(1234.56)
        assert abs(result - Decimal("1234.56")) < Decimal("0.001")

    def test_parse_with_whitespace(self):
        """Whitespace is stripped."""
        assert parse_fints_amount("  1234,56  ") == Decimal("1234.56")

    def test_parse_empty_raises(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_fints_amount("")

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_amount(None)

    def test_parse_invalid_raises(self):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse amount"):
            parse_fints_amount("abc")


class TestSerializeFintAmount:
    """Tests for serialize_fints_amount serializer."""

    def test_serialize_decimal(self):
        """Serialize Decimal to German format."""
        assert serialize_fints_amount(Decimal("1234.56")) == "1234,56"
        assert serialize_fints_amount(Decimal("0.01")) == "0,01"
        assert serialize_fints_amount(Decimal("1234")) == "1234"


# =============================================================================
# Boolean Validator Tests
# =============================================================================


class TestParseFintBool:
    """Tests for parse_fints_bool validator."""

    def test_parse_j_is_true(self):
        """'J' parses to True."""
        assert parse_fints_bool("J") is True
        assert parse_fints_bool("j") is True

    def test_parse_n_is_false(self):
        """'N' parses to False."""
        assert parse_fints_bool("N") is False
        assert parse_fints_bool("n") is False

    def test_parse_bool_passthrough(self):
        """Boolean objects pass through unchanged."""
        assert parse_fints_bool(True) is True
        assert parse_fints_bool(False) is False

    def test_parse_with_whitespace(self):
        """Whitespace is stripped."""
        assert parse_fints_bool("  J  ") is True

    def test_parse_invalid_raises(self):
        """Invalid value raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS boolean"):
            parse_fints_bool("Yes")
        with pytest.raises(ValueError, match="Cannot parse FinTS boolean"):
            parse_fints_bool("1")

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_bool(None)


class TestSerializeFintBool:
    """Tests for serialize_fints_bool serializer."""

    def test_serialize_true(self):
        """True serializes to 'J'."""
        assert serialize_fints_bool(True) == "J"

    def test_serialize_false(self):
        """False serializes to 'N'."""
        assert serialize_fints_bool(False) == "N"


# =============================================================================
# Numeric Validator Tests
# =============================================================================


class TestParseFintNumeric:
    """Tests for parse_fints_numeric validator."""

    def test_parse_valid_string(self):
        """Parse valid numeric string."""
        assert parse_fints_numeric("123") == 123
        assert parse_fints_numeric("0") == 0
        assert parse_fints_numeric("999999") == 999999

    def test_parse_int_passthrough(self):
        """Integer objects pass through."""
        assert parse_fints_numeric(123) == 123

    def test_parse_with_whitespace(self):
        """Whitespace is stripped."""
        assert parse_fints_numeric("  123  ") == 123

    def test_parse_leading_zeros_allowed(self):
        """Leading zeros are allowed for fixed-width numeric fields like message_size."""
        assert parse_fints_numeric("0123") == 123
        assert parse_fints_numeric("000000000123") == 123

    def test_parse_zero_is_valid(self):
        """'0' is a valid value."""
        assert parse_fints_numeric("0") == 0

    def test_parse_empty_raises(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_fints_numeric("")

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_numeric(None)

    def test_parse_non_numeric_raises(self):
        """Non-numeric string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse numeric"):
            parse_fints_numeric("abc")


# =============================================================================
# Digits Validator Tests
# =============================================================================


class TestParseFintDigits:
    """Tests for parse_fints_digits validator."""

    def test_parse_digits_string(self):
        """Parse string of digits."""
        assert parse_fints_digits("123") == "123"
        assert parse_fints_digits("00123") == "00123"  # Leading zeros allowed
        assert parse_fints_digits("000") == "000"

    def test_parse_empty_string(self):
        """Empty string is valid for digits."""
        assert parse_fints_digits("") == ""

    def test_parse_int_converts_to_string(self):
        """Integer converts to string."""
        assert parse_fints_digits(123) == "123"

    def test_parse_with_whitespace(self):
        """Whitespace is stripped."""
        assert parse_fints_digits("  123  ") == "123"

    def test_parse_non_digits_raises(self):
        """Non-digit characters raise ValueError."""
        with pytest.raises(ValueError, match="must contain only digits"):
            parse_fints_digits("12a34")

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_digits(None)


# =============================================================================
# Text/Code/Binary Validator Tests
# =============================================================================


class TestParseFintText:
    """Tests for parse_fints_text validator."""

    def test_parse_text(self):
        """Parse text string."""
        assert parse_fints_text("Hello World") == "Hello World"
        assert parse_fints_text("") == ""

    def test_parse_converts_to_string(self):
        """Non-string values convert to string."""
        assert parse_fints_text(123) == "123"

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_text(None)


class TestParseFintCode:
    """Tests for parse_fints_code validator."""

    def test_parse_code(self):
        """Parse code string."""
        assert parse_fints_code("EUR") == "EUR"
        assert parse_fints_code("999") == "999"

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_code(None)


class TestParseFintBinary:
    """Tests for parse_fints_binary validator."""

    def test_parse_bytes(self):
        """Parse bytes."""
        assert parse_fints_binary(b"\x00\x01\x02") == b"\x00\x01\x02"

    def test_parse_bytearray(self):
        """Parse bytearray."""
        assert parse_fints_binary(bytearray([0, 1, 2])) == b"\x00\x01\x02"

    def test_parse_none_raises(self):
        """None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_fints_binary(None)

    def test_parse_string_raises(self):
        """String raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse FinTS binary"):
            parse_fints_binary("hello")


# =============================================================================
# Annotated Type Tests with Pydantic Models
# =============================================================================


class TestFinTSDateAnnotated:
    """Tests for FinTSDate annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses FinTS date format."""

        class Model(BaseModel):
            date: FinTSDate

        m = Model(date="20231225")
        assert m.date == date(2023, 12, 25)

    def test_model_serialization(self):
        """Model serializes to FinTS date format."""

        class Model(BaseModel):
            date: FinTSDate

        m = Model(date=date(2023, 12, 25))
        dumped = m.model_dump(mode="json")
        assert dumped["date"] == "20231225"

    def test_model_validation_error(self):
        """Invalid date raises ValidationError."""

        class Model(BaseModel):
            date: FinTSDate

        with pytest.raises(ValidationError):
            Model(date="invalid")


class TestFinTSTimeAnnotated:
    """Tests for FinTSTime annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses FinTS time format."""

        class Model(BaseModel):
            time: FinTSTime

        m = Model(time="143022")
        assert m.time == time(14, 30, 22)

    def test_model_serialization(self):
        """Model serializes to FinTS time format."""

        class Model(BaseModel):
            time: FinTSTime

        m = Model(time=time(14, 30, 22))
        dumped = m.model_dump(mode="json")
        assert dumped["time"] == "143022"


class TestFinTSAmountAnnotated:
    """Tests for FinTSAmount annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses FinTS amount format."""

        class Model(BaseModel):
            amount: FinTSAmount

        m = Model(amount="1234,56")
        assert m.amount == Decimal("1234.56")

    def test_model_serialization(self):
        """Model serializes to FinTS amount format."""

        class Model(BaseModel):
            amount: FinTSAmount

        m = Model(amount=Decimal("1234.56"))
        dumped = m.model_dump(mode="json")
        assert dumped["amount"] == "1234,56"


class TestFinTSBoolAnnotated:
    """Tests for FinTSBool annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses FinTS boolean format."""

        class Model(BaseModel):
            active: FinTSBool

        assert Model(active="J").active is True
        assert Model(active="N").active is False

    def test_model_serialization(self):
        """Model serializes to FinTS boolean format."""

        class Model(BaseModel):
            active: FinTSBool

        assert Model(active=True).model_dump(mode="json")["active"] == "J"
        assert Model(active=False).model_dump(mode="json")["active"] == "N"


class TestFinTSNumericAnnotated:
    """Tests for FinTSNumeric annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses FinTS numeric format."""

        class Model(BaseModel):
            count: FinTSNumeric

        m = Model(count="123")
        assert m.count == 123

    def test_model_serialization(self):
        """Model serializes to FinTS numeric format."""

        class Model(BaseModel):
            count: FinTSNumeric

        m = Model(count=123)
        dumped = m.model_dump(mode="json")
        assert dumped["count"] == "123"


class TestFinTSCurrencyAnnotated:
    """Tests for FinTSCurrency annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses currency code."""

        class Model(BaseModel):
            currency: FinTSCurrency

        m = Model(currency="EUR")
        assert m.currency == "EUR"

    def test_model_validation_length(self):
        """Currency must be exactly 3 characters."""

        class Model(BaseModel):
            currency: FinTSCurrency

        with pytest.raises(ValidationError):
            Model(currency="EU")

        with pytest.raises(ValidationError):
            Model(currency="EURO")


class TestFinTSCountryAnnotated:
    """Tests for FinTSCountry annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses country code."""

        class Model(BaseModel):
            country: FinTSCountry

        m = Model(country="280")
        assert m.country == "280"

    def test_model_validation_pattern(self):
        """Country must be 3 digits."""

        class Model(BaseModel):
            country: FinTSCountry

        with pytest.raises(ValidationError):
            Model(country="DE")

        with pytest.raises(ValidationError):
            Model(country="2800")


class TestFinTSIDAnnotated:
    """Tests for FinTSID annotated type in Pydantic models."""

    def test_model_parsing(self):
        """Model parses ID."""

        class Model(BaseModel):
            id: FinTSID

        m = Model(id="123456789")
        assert m.id == "123456789"

    def test_model_validation_max_length(self):
        """ID must be max 30 characters."""

        class Model(BaseModel):
            id: FinTSID

        # 30 chars is OK
        Model(id="a" * 30)

        # 31 chars fails
        with pytest.raises(ValidationError):
            Model(id="a" * 31)


# =============================================================================
# Optional Type Tests
# =============================================================================


class TestOptionalTypes:
    """Tests for optional FinTS types in models."""

    def test_optional_date(self):
        """Optional date can be None."""

        class Model(BaseModel):
            date: FinTSDate | None = None

        m = Model()
        assert m.date is None

        m = Model(date="20231225")
        assert m.date == date(2023, 12, 25)

    def test_optional_amount(self):
        """Optional amount can be None."""

        class Model(BaseModel):
            amount: FinTSAmount | None = None

        m = Model()
        assert m.amount is None

        m = Model(amount="1234,56")
        assert m.amount == Decimal("1234.56")


# =============================================================================
# Combined Model Test
# =============================================================================


class TestCombinedModel:
    """Tests for model using multiple FinTS types."""

    def test_full_model(self):
        """Model with multiple FinTS types."""

        class Transaction(BaseModel):
            date: FinTSDate
            time: FinTSTime | None = None
            amount: FinTSAmount
            currency: FinTSCurrency
            booked: FinTSBool
            reference: FinTSID | None = None

        # Parse from wire format
        tx = Transaction(
            date="20231225",
            time="143022",
            amount="1234,56",
            currency="EUR",
            booked="J",
            reference="TX123",
        )

        assert tx.date == date(2023, 12, 25)
        assert tx.time == time(14, 30, 22)
        assert tx.amount == Decimal("1234.56")
        assert tx.currency == "EUR"
        assert tx.booked is True
        assert tx.reference == "TX123"

        # Serialize to wire format
        dumped = tx.model_dump(mode="json")
        assert dumped["date"] == "20231225"
        assert dumped["time"] == "143022"
        assert dumped["amount"] == "1234,56"
        assert dumped["currency"] == "EUR"
        assert dumped["booked"] == "J"
        assert dumped["reference"] == "TX123"

