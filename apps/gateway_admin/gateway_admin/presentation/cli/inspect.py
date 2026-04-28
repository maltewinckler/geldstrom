"""Typer CLI command for inspecting backend state."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

from gateway_admin.application.queries import InspectBackendStateQuery
from gateway_admin.presentation.cli._common import build_context

app = typer.Typer(name="inspect", help="Inspect gateway backend state.")
console = Console()


@app.command("state")
def inspect_state(
    blz: Annotated[
        str | None,
        typer.Option("--blz", help="Look up a specific institute by BLZ"),
    ] = None,
) -> None:
    """Print a sanitized snapshot of backend state."""

    async def _run() -> None:
        async with build_context() as ctx:
            report = await InspectBackendStateQuery.from_factory(ctx.repo_factory)(
                blz=blz
            )

        console.print(f"DB connectivity: [green]{report.db_connectivity}[/green]")
        console.print(
            f"Users: {report.total_user_count} total, {report.active_user_count} active"
        )
        console.print(f"Institutes: {report.institute_count}")
        if report.selected_institute:
            inst = report.selected_institute
            console.print(f"Institute ({inst.blz}): {inst.name} - {inst.city}")
        if report.product_registration:
            console.print(
                f"Product registration: v{report.product_registration.product_version}"
            )
        else:
            console.print("Product registration: [yellow]not configured[/yellow]")

    asyncio.run(_run())
