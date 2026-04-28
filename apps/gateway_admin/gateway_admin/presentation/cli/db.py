"""Typer CLI commands for database management."""

from __future__ import annotations

import asyncio

import typer
from gateway_contracts.schema import metadata
from rich.console import Console
from sqlalchemy.ext.asyncio import create_async_engine

from gateway_admin.application.commands import (
    InitializeDatabaseCommand,
    UpdateProductRegistrationCommand,  # noqa: F401 — imported for patch-ability in tests
)
from gateway_admin.config import get_settings
from gateway_admin.presentation.cli._common import build_context

app = typer.Typer(name="db", help="Manage the database schema.")
console = Console()


async def _run_init() -> None:
    """Async implementation of `db init` — exposed for unit testing."""
    async with build_context() as ctx:
        await InitializeDatabaseCommand.from_factory(ctx.repo_factory)()
    console.print(f"[green]Tables ready:[/green] {', '.join(sorted(metadata.tables))}")


@app.command("init")
def init_db() -> None:
    """Create the database, tables, and gateway DB user if they do not exist (idempotent)."""
    asyncio.run(_run_init())


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
