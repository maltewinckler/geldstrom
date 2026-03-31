"""SQL repository for canonical FinTS institute records."""

from __future__ import annotations

from gateway_contracts.schema import fints_institutes_table
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.banking_gateway import (
    BankLeitzahl,
    FinTSInstitute,
    FinTSInstituteRepository,
)


class SQLFinTSInstituteRepository(FinTSInstituteRepository):
    """Persist canonical institute records in a SQL database."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        statement = select(fints_institutes_table).where(
            fints_institutes_table.c.blz == blz.value
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_institute(row) if row is not None else None

    async def list_all(self) -> list[FinTSInstitute]:
        statement = select(fints_institutes_table).order_by(
            fints_institutes_table.c.blz.asc()
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return [_row_to_institute(row) for row in rows]


def _row_to_institute(row: object) -> FinTSInstitute:
    mapping = dict(row)
    return FinTSInstitute(
        blz=BankLeitzahl(mapping["blz"]),
        bic=mapping["bic"],
        name=mapping["name"],
        city=mapping["city"],
        organization=mapping["organization"],
        pin_tan_url=mapping["pin_tan_url"],
        fints_version=mapping["fints_version"],
        last_source_update=mapping["last_source_update"],
    )
