"""Integration tests for the PostgreSQL institute repository."""

from __future__ import annotations

from datetime import date

from gateway_contracts.schema import fints_institutes_table

from gateway.domain.banking_gateway import (
    BankLeitzahl,
    FinTSInstitute,
)
from gateway.infrastructure.persistence.sqlalchemy import (
    FinTSInstituteRepositorySqlAlchemy,
)


async def _seed_institutes(engine, *institutes: FinTSInstitute) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            fints_institutes_table.insert(),
            [
                {
                    "blz": inst.blz.value,
                    "bic": inst.bic,
                    "name": inst.name,
                    "city": inst.city,
                    "organization": inst.organization,
                    "pin_tan_url": inst.pin_tan_url,
                    "fints_version": inst.fints_version,
                    "last_source_update": inst.last_source_update,
                    "source_row_checksum": "seeded",
                    "source_payload": {},
                }
                for inst in institutes
            ],
        )


def test_institute_repository_list_all(postgres_engine, async_runner) -> None:
    async_runner(
        _seed_institutes(
            postgres_engine, _institute("12345678"), _institute("87654321")
        )
    )
    repository = FinTSInstituteRepositorySqlAlchemy(postgres_engine)

    institutes = async_runner(repository.list_all())

    assert [i.blz.value for i in institutes] == ["12345678", "87654321"]


def test_institute_repository_get_by_blz(postgres_engine, async_runner) -> None:
    expected = _institute("12345678")
    async_runner(_seed_institutes(postgres_engine, expected))
    repository = FinTSInstituteRepositorySqlAlchemy(postgres_engine)

    loaded = async_runner(repository.get_by_blz(BankLeitzahl("12345678")))

    assert loaded == expected


def test_institute_repository_returns_none_for_unknown_blz(
    postgres_engine, async_runner
) -> None:
    repository = FinTSInstituteRepositorySqlAlchemy(postgres_engine)

    loaded = async_runner(repository.get_by_blz(BankLeitzahl("12345678")))

    assert loaded is None


def _institute(blz: str) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl(blz),
        bic="GENODEF1ABC",
        name=f"Bank {blz}",
        city="Berlin",
        organization="Example Org",
        pin_tan_url="https://bank.example/fints",
        fints_version="FinTS V3.0",
        last_source_update=date(2026, 3, 7),
    )
