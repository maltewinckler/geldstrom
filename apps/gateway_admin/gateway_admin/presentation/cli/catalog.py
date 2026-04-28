"""Typer CLI commands for managing the institute catalog."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from gateway_admin.application.commands import SyncInstituteCatalogCommand
from gateway_admin.presentation.cli._common import build_context

app = typer.Typer(name="catalog", help="Manage the FinTS institute catalog.")
console = Console()


@app.command("sync")
def sync_catalog(
    csv_path: Annotated[
        Path, typer.Argument(help="Path to the Bundesbank FinTS institute CSV file")
    ],
) -> None:
    """Sync the institute catalog from a CSV file."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await SyncInstituteCatalogCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(csv_path)
            except Exception as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(f"[green]Synced {result.loaded_count} institutes.[/green]")
        if result.skipped_rows:
            console.print(f"[yellow]{len(result.skipped_rows)} rows skipped:[/yellow]")
            table = Table("BLZ", "Name", "Reason", show_lines=False)
            for row in result.skipped_rows:
                table.add_row(row.blz, row.name, row.reason)
            console.print(table)

    asyncio.run(_run())
