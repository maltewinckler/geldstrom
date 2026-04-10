"""Tests for the bank lookup router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from gateway.application.banking.dtos.lookup_bank import BankInfoEnvelope
from gateway.application.banking.queries.lookup_bank import LookupBankQuery
from gateway.application.common import InstitutionNotFoundError, ValidationError
from gateway.presentation.http.dependencies import get_factory
from gateway.presentation.http.routers import lookup


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(lookup.router)
    app.dependency_overrides[get_factory] = lambda: MagicMock()
    return app


_ENVELOPE = BankInfoEnvelope(
    blz="10010010",
    bic="PBNKDEFFXXX",
    name="Postbank",
    organization="BdB",
    is_fints_capable=True,
)

_AUTH_HEADER = {"Authorization": "Bearer prefix.secret"}


def test_lookup_returns_200_with_bank_info() -> None:
    use_case = AsyncMock(return_value=_ENVELOPE)
    with patch.object(LookupBankQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app())
        resp = client.get("/v1/lookup/10010010", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    body = resp.json()
    assert body["blz"] == "10010010"
    assert body["bic"] == "PBNKDEFFXXX"
    assert body["name"] == "Postbank"
    assert body["organization"] == "BdB"
    assert body["is_fints_capable"] is True


def test_lookup_returns_401_without_auth_header() -> None:
    use_case = AsyncMock(return_value=_ENVELOPE)
    with patch.object(LookupBankQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        resp = client.get("/v1/lookup/10010010")

    assert resp.status_code == 401


def test_lookup_returns_404_when_institution_not_found() -> None:
    use_case = AsyncMock(
        side_effect=InstitutionNotFoundError("No institute found for BLZ 99999999")
    )
    with patch.object(LookupBankQuery, "from_factory", return_value=use_case):
        from gateway.application.common import ApplicationError
        from gateway.presentation.http.middleware.exception_handlers import (
            application_error_handler,
        )

        app = _make_app()
        app.add_exception_handler(ApplicationError, application_error_handler)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/lookup/99999999", headers=_AUTH_HEADER)

    assert resp.status_code == 404
    assert resp.json()["error"] == "institution_not_found"


def test_lookup_returns_422_when_validation_error() -> None:
    use_case = AsyncMock(
        side_effect=ValidationError("BankLeitzahl must be an 8-digit string")
    )
    with patch.object(LookupBankQuery, "from_factory", return_value=use_case):
        from gateway.application.common import ApplicationError
        from gateway.presentation.http.middleware.exception_handlers import (
            application_error_handler,
        )

        app = _make_app()
        app.add_exception_handler(ApplicationError, application_error_handler)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/lookup/INVALID", headers=_AUTH_HEADER)

    assert resp.status_code == 422
    assert resp.json()["error"] == "validation_error"
