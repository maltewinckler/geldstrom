"""Tests for admin CLI domain models."""

from __future__ import annotations

from datetime import date

import pytest

from gateway_admin.domain.errors import DomainError
from gateway_admin.domain.institutes import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
    InstituteSelectionPolicy,
)


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


def test_selection_raises_on_empty_candidates() -> None:
    with pytest.raises(DomainError):
        InstituteSelectionPolicy.select([])
