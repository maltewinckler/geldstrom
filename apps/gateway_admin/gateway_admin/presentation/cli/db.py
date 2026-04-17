"""Typer CLI commands for database management."""

from __future__ import annotations

import asyncio

import typer
from gateway_contracts.schema import metadata
from rich.console import Console
from sqlalchemy.ext.asyncio import create_async_engine

from gateway_admin.application.commands import (
    InitializeDatabaseCommand,
    UpdateProductRegistrationCommand,
)
from gateway_admin.config import get_settings
from gateway_admin.presentation.cli._common import build_context

app = typer.Typer(name="db", help="Manage the database schema.")
console = Console()


@app.command("init")
def init_db() -> None:
    """Create the database, tables, and gateway DB user if they do not exist (idempotent)."""

    async def _run() -> None:
        s = get_settings()
        async with build_context() as ctx:
            await InitializeDatabaseCommand.from_factory(ctx.repo_factory)()
            result = await UpdateProductRegistrationCommand.from_factory(
                ctx.repo_factory,
                ctx.service_factory,
                product_version=s.fints_product_version,
            )(s.fints_product_registration_key)
        console.print(
            f"[green]Tables ready:[/green] {', '.join(sorted(metadata.tables))}"
        )
        console.print(
            f"[green]Product registration ready.[/green] version={result.product_version}"
        )

    asyncio.run(_run())


@app.command("reset")
def reset_db(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Delete all records from every table (structure is kept)."""
    if not yes:
        typer.confirm("This will delete all data. Continue?", abort=True)

    async def _run() -> None:
        s = get_settings()
        engine = create_async_engine(s.database_url)
        try:
            async with engine.begin() as conn:
                for table in reversed(metadata.sorted_tables):
                    await conn.execute(table.delete())
        finally:
            await engine.dispose()

        console.print(
            f"[green]All records deleted from:[/green] "
            f"{', '.join(t.name for t in reversed(metadata.sorted_tables))}"
        )

    asyncio.run(_run())
