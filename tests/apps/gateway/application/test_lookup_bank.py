"""Tests for the LookupBank query."""

from __future__ import annotations

import asyncio

import pytest

from gateway.application.banking.queries.lookup_bank import LookupBankQuery
from gateway.application.common import InstitutionNotFoundError, ValidationError
from gateway.domain.banking_gateway import BankLeitzahl, FinTSInstitute
from tests.apps.gateway.fakes import FakeInstituteCache


def _institute(
    blz: str = "10010010",
    *,
    bic: str | None = "PBNKDEFFXXX",
    name: str = "Postbank",
    organization: str | None = "BdB",
    pin_tan_url: str | None = "https://hbci.postbank.de/banking/hbci.do",
) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl(blz),
        bic=bic,
        name=name,
        city="Berlin",
        organization=organization,
        pin_tan_url=pin_tan_url,
        fints_version="FinTS V3.0",
        last_source_update=None,
    )


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_lookup_returns_correct_envelope() -> None:
    query = LookupBankQuery(bank_catalog=FakeInstituteCache([_institute()]))

    result = _run(query("10010010"))

    assert result.blz == "10010010"
    assert result.bic == "PBNKDEFFXXX"
    assert result.name == "Postbank"
    assert result.organization == "BdB"
    assert result.is_fints_capable is True


def test_lookup_is_fints_capable_false_when_no_pin_tan_url() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([_institute(pin_tan_url=None)])
    )

    result = _run(query("10010010"))

    assert result.is_fints_capable is False


def test_lookup_handles_none_bic_and_organization() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([_institute(bic=None, organization=None)])
    )

    result = _run(query("10010010"))

    assert result.bic is None
    assert result.organization is None


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


def test_lookup_raises_institution_not_found_for_unknown_blz() -> None:
    query = LookupBankQuery(bank_catalog=FakeInstituteCache([]))

    with pytest.raises(InstitutionNotFoundError):
        _run(query("99999999"))


def test_lookup_raises_validation_error_for_invalid_blz_format() -> None:
    query = LookupBankQuery(bank_catalog=FakeInstituteCache([]))

    with pytest.raises(ValidationError):
        _run(query("INVALID"))


def test_lookup_raises_validation_error_for_short_blz() -> None:
    query = LookupBankQuery(bank_catalog=FakeInstituteCache([]))

    with pytest.raises(ValidationError):
        _run(query("1234"))


def test_lookup_raises_validation_error_not_domain_error_for_bad_blz() -> None:
    """DomainError must be translated — not allowed to leak to presentation."""
    from gateway.domain.errors import DomainError

    query = LookupBankQuery(bank_catalog=FakeInstituteCache([]))

    with pytest.raises(ValidationError):
        _run(query("TOOLONG!"))

    # Confirm DomainError itself is NOT raised
    try:
        _run(query("TOOLONG!"))
    except ValidationError:
        pass
    except DomainError:
        pytest.fail("DomainError leaked through LookupBankQuery — must be translated")
