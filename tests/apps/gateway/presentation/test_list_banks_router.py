"""Tests for the list banks router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from gateway.application.banking.dtos.lookup_bank import BankInfoEnvelope
from gateway.application.banking.queries.list_banks import ListBanksQuery
from gateway.presentation.http.dependencies import get_factory
from gateway.presentation.http.routers import lookup

_AUTH_HEADER = {"Authorization": "Bearer prefix.secret"}

_ENVELOPES = [
    BankInfoEnvelope(
        blz="10010010",
        bic="PBNKDEFFXXX",
        name="Postbank",
        organization="BdB",
        is_fints_capable=True,
    ),
    BankInfoEnvelope(
        blz="20010020",
        bic=None,
        name="Deutsche Bank",
        organization=None,
        is_fints_capable=False,
    ),
]


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(lookup.router)
    app.dependency_overrides[get_factory] = lambda: MagicMock()
    return app


def test_list_banks_returns_200_with_all_banks() -> None:
    use_case = AsyncMock(return_value=_ENVELOPES)
    with patch.object(ListBanksQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app())
        resp = client.get("/v1/lookup", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    body = resp.json()
    assert "banks" in body
    assert len(body["banks"]) == 2
    blzs = {b["blz"] for b in body["banks"]}
    assert blzs == {"10010010", "20010020"}


def test_list_banks_returns_empty_banks_list_when_catalog_is_empty() -> None:
    use_case = AsyncMock(return_value=[])
    with patch.object(ListBanksQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app())
        resp = client.get("/v1/lookup", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    assert resp.json() == {"banks": []}


def test_list_banks_returns_401_without_auth_header() -> None:
    use_case = AsyncMock(return_value=_ENVELOPES)
    with patch.object(ListBanksQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.get("/v1/lookup")

    assert resp.status_code == 401
