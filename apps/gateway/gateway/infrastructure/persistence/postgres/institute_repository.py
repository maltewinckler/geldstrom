"""PostgreSQL repository for canonical FinTS institute records."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    FinTSInstituteRepository,
    InstituteEndpoint,
)

from .schema import fints_institutes_table


class PostgresFinTSInstituteRepository(FinTSInstituteRepository):
    """Persist canonical institute records in PostgreSQL."""

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

    async def replace_catalog(self, institutes: list[FinTSInstitute]) -> None:
        payload = [
            {
                "blz": institute.blz.value,
                "bic": institute.bic.value if institute.bic else None,
                "name": institute.name,
                "city": institute.city,
                "organization": institute.organization,
                "pin_tan_url": institute.pin_tan_url.value
                if institute.pin_tan_url
                else None,
                "fints_version": institute.fints_version,
                "last_source_update": institute.last_source_update,
                "source_row_checksum": institute.source_row_checksum,
                "source_payload": institute.source_payload,
            }
            for institute in institutes
        ]
        async with self._engine.begin() as connection:
            await connection.execute(delete(fints_institutes_table))
            if payload:
                await connection.execute(fints_institutes_table.insert(), payload)


def _row_to_institute(row: object) -> FinTSInstitute:
    mapping = dict(row)
    return FinTSInstitute(
        blz=BankLeitzahl(mapping["blz"]),
        bic=Bic(mapping["bic"]) if mapping["bic"] else None,
        name=mapping["name"],
        city=mapping["city"],
        organization=mapping["organization"],
        pin_tan_url=(
            InstituteEndpoint(mapping["pin_tan_url"])
            if mapping["pin_tan_url"]
            else None
        ),
        fints_version=mapping["fints_version"],
        last_source_update=mapping["last_source_update"],
        source_row_checksum=mapping["source_row_checksum"],
        source_payload=dict(mapping["source_payload"]),
    )
