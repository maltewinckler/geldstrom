"""Tests for the LookupBank query."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.application.banking.queries.lookup_bank import LookupBankQuery
from gateway.application.common import InstitutionNotFoundError, ValidationError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import BankLeitzahl, FinTSInstitute
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from tests.apps.gateway.fakes import FakeConsumerCache, FakeInstituteCache


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def _make_auth() -> AuthenticateConsumerQuery:
    consumer = ApiConsumer(
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="consumer@example.com",
        api_key_hash=ApiKeyHash("12345678.api-key-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )
    return AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier()
    )


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


_VALID_KEY = "12345678.api-key-1"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_lookup_returns_correct_envelope() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([_institute()]),
        authenticate_consumer=_make_auth(),
    )

    result = _run(query("10010010", _VALID_KEY))

    assert result.blz == "10010010"
    assert result.bic == "PBNKDEFFXXX"
    assert result.name == "Postbank"
    assert result.organization == "BdB"
    assert result.is_fints_capable is True


def test_lookup_is_fints_capable_false_when_no_pin_tan_url() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([_institute(pin_tan_url=None)]),
        authenticate_consumer=_make_auth(),
    )

    result = _run(query("10010010", _VALID_KEY))

    assert result.is_fints_capable is False


def test_lookup_handles_none_bic_and_organization() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([_institute(bic=None, organization=None)]),
        authenticate_consumer=_make_auth(),
    )

    result = _run(query("10010010", _VALID_KEY))

    assert result.bic is None
    assert result.organization is None


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


def test_lookup_raises_institution_not_found_for_unknown_blz() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([]),
        authenticate_consumer=_make_auth(),
    )

    with pytest.raises(InstitutionNotFoundError):
        _run(query("99999999", _VALID_KEY))


def test_lookup_raises_validation_error_for_invalid_blz_format() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([]),
        authenticate_consumer=_make_auth(),
    )

    with pytest.raises(ValidationError):
        _run(query("INVALID", _VALID_KEY))


def test_lookup_raises_validation_error_for_short_blz() -> None:
    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([]),
        authenticate_consumer=_make_auth(),
    )

    with pytest.raises(ValidationError):
        _run(query("1234", _VALID_KEY))


def test_lookup_raises_unauthorized_for_invalid_api_key() -> None:
    from gateway.application.common import UnauthorizedError

    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([_institute()]),
        authenticate_consumer=_make_auth(),
    )

    with pytest.raises(UnauthorizedError):
        _run(query("10010010", "00000000.wrong-key"))


def test_lookup_raises_validation_error_not_domain_error_for_bad_blz() -> None:
    """DomainError must be translated — not allowed to leak to presentation."""
    from gateway.domain.errors import DomainError

    query = LookupBankQuery(
        bank_catalog=FakeInstituteCache([]),
        authenticate_consumer=_make_auth(),
    )

    with pytest.raises(ValidationError):
        _run(query("TOOLONG!", _VALID_KEY))

    # Confirm DomainError itself is NOT raised
    try:
        _run(query("TOOLONG!", _VALID_KEY))
    except ValidationError:
        pass
    except DomainError:
        pytest.fail("DomainError leaked through LookupBankQuery — must be translated")
