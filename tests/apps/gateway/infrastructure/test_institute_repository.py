"""Integration tests for the PostgreSQL institute repository."""

from __future__ import annotations

from datetime import date

from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)
from gateway.infrastructure.persistence.postgres import PostgresFinTSInstituteRepository


def test_institute_repository_replaces_catalog(postgres_engine, async_runner) -> None:
    repository = PostgresFinTSInstituteRepository(postgres_engine)

    async_runner(
        repository.replace_catalog([_institute("12345678"), _institute("87654321")])
    )

    institutes = async_runner(repository.list_all())

    assert [institute.blz.value for institute in institutes] == ["12345678", "87654321"]


def test_institute_repository_get_by_blz(postgres_engine, async_runner) -> None:
    repository = PostgresFinTSInstituteRepository(postgres_engine)
    expected = _institute("12345678")

    async_runner(repository.replace_catalog([expected]))

    loaded = async_runner(repository.get_by_blz(BankLeitzahl("12345678")))

    assert loaded == expected


def test_institute_repository_returns_none_for_unknown_blz(
    postgres_engine, async_runner
) -> None:
    repository = PostgresFinTSInstituteRepository(postgres_engine)

    loaded = async_runner(repository.get_by_blz(BankLeitzahl("12345678")))

    assert loaded is None


def _institute(blz: str) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl(blz),
        bic=Bic("GENODEF1ABC"),
        name=f"Bank {blz}",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint("https://bank.example/fints"),
        fints_version="FinTS V3.0",
        last_source_update=date(2026, 3, 7),
        source_row_checksum=f"checksum-{blz}",
        source_payload={"blz": blz},
    )
