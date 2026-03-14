"""Tests for the institution catalog domain."""

from datetime import date

import pytest

from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
    InstituteSelectionPolicy,
)
from gateway.domain.shared import DomainError


def _build_institute(
    *,
    checksum: str,
    pin_tan_url: str | None,
    last_source_update: date | None,
) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic=Bic("GENODEF1ABC"),
        name="Example Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint(pin_tan_url) if pin_tan_url is not None else None,
        fints_version="3.0",
        last_source_update=last_source_update,
        source_row_checksum=checksum,
        source_payload={"checksum": checksum},
    )


def test_bankleitzahl_rejects_invalid_values() -> None:
    with pytest.raises(DomainError, match="8-digit"):
        BankLeitzahl("123")


def test_bic_accepts_11_character_codes_and_normalizes_case() -> None:
    bic = Bic("genodef1abc")

    assert bic.value == "GENODEF1ABC"


def test_bic_rejects_invalid_length() -> None:
    with pytest.raises(DomainError, match="8 or 11"):
        Bic("ABC")


def test_selection_prefers_pin_tan_capable_rows() -> None:
    selected = InstituteSelectionPolicy.select(
        [
            _build_institute(
                checksum="z-checksum",
                pin_tan_url=None,
                last_source_update=date(2026, 1, 1),
            ),
            _build_institute(
                checksum="a-checksum",
                pin_tan_url="https://bank.example/fints",
                last_source_update=date(2025, 1, 1),
            ),
        ]
    )

    assert selected.source_row_checksum == "a-checksum"


def test_selection_prefers_more_recent_source_update_after_capability() -> None:
    selected = InstituteSelectionPolicy.select(
        [
            _build_institute(
                checksum="older",
                pin_tan_url="https://bank.example/one",
                last_source_update=date(2025, 1, 1),
            ),
            _build_institute(
                checksum="newer",
                pin_tan_url="https://bank.example/two",
                last_source_update=date(2026, 1, 1),
            ),
        ]
    )

    assert selected.source_row_checksum == "newer"


def test_selection_prefers_deterministic_checksum_when_other_fields_tie() -> None:
    selected = InstituteSelectionPolicy.select(
        [
            _build_institute(
                checksum="z-last",
                pin_tan_url="https://bank.example/one",
                last_source_update=date(2026, 1, 1),
            ),
            _build_institute(
                checksum="a-first",
                pin_tan_url="https://bank.example/two",
                last_source_update=date(2026, 1, 1),
            ),
        ]
    )

    assert selected.source_row_checksum == "a-first"
