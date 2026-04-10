"""Tests for the ListBanks query."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.application.banking.queries.list_banks import ListBanksQuery
from gateway.application.common import UnauthorizedError
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
    name: str = "Postbank",
    pin_tan_url: str | None = "https://hbci.postbank.de/banking/hbci.do",
) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl(blz),
        bic="PBNKDEFFXXX",
        name=name,
        city="Berlin",
        organization="BdB",
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


def test_list_banks_returns_all_institutes() -> None:
    institutes = [
        _institute("10010010", "Postbank"),
        _institute("20010020", "Deutsche Bank"),
    ]
    query = ListBanksQuery(
        bank_catalog=FakeInstituteCache(institutes),
        authenticate_consumer=_make_auth(),
    )

    results = _run(query(_VALID_KEY))

    blzs = {r.blz for r in results}
    assert blzs == {"10010010", "20010020"}
    assert all(r.is_fints_capable is True for r in results)


def test_list_banks_returns_empty_list_for_empty_catalog() -> None:
    query = ListBanksQuery(
        bank_catalog=FakeInstituteCache([]),
        authenticate_consumer=_make_auth(),
    )

    results = _run(query(_VALID_KEY))

    assert results == []


def test_list_banks_maps_is_fints_capable_correctly() -> None:
    institutes = [
        _institute("10010010", pin_tan_url="https://bank.example/fints"),
        _institute("20010020", pin_tan_url=None),
    ]
    query = ListBanksQuery(
        bank_catalog=FakeInstituteCache(institutes),
        authenticate_consumer=_make_auth(),
    )

    results = _run(query(_VALID_KEY))

    capable = {r.blz: r.is_fints_capable for r in results}
    assert capable["10010010"] is True
    assert capable["20010020"] is False


# ---------------------------------------------------------------------------
# Auth failure
# ---------------------------------------------------------------------------


def test_list_banks_raises_unauthorized_for_invalid_api_key() -> None:
    query = ListBanksQuery(
        bank_catalog=FakeInstituteCache([_institute()]),
        authenticate_consumer=_make_auth(),
    )

    with pytest.raises(UnauthorizedError):
        _run(query("00000000.wrong-key"))
