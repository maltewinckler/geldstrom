"""Tests for the in-memory institute cache."""

from __future__ import annotations

import asyncio
from datetime import date

from gateway.domain.banking_gateway import (
    BankLeitzahl,
    FinTSInstitute,
)
from gateway.infrastructure.cache.memory import InMemoryFinTSInstituteCache


def test_institute_cache_loads_and_reads_by_blz() -> None:
    cache = InMemoryFinTSInstituteCache()
    institute = _institute("12345678")

    asyncio.run(cache.load([institute]))

    loaded = asyncio.run(cache.get_by_blz(BankLeitzahl("12345678")))

    assert loaded == institute


def test_institute_cache_replaces_existing_index_on_load() -> None:
    cache = InMemoryFinTSInstituteCache()
    asyncio.run(cache.load([_institute("12345678")]))

    asyncio.run(cache.load([_institute("87654321")]))

    assert asyncio.run(cache.get_by_blz(BankLeitzahl("12345678"))) is None
    assert asyncio.run(cache.get_by_blz(BankLeitzahl("87654321"))) == _institute(
        "87654321"
    )


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
