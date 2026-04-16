"""Typer CLI commands for managing the shared product registration."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

from gateway_admin.application.commands import UpdateProductRegistrationCommand
from gateway_admin.domain.errors import ValidationError

from ._common import build_context

app = typer.Typer(name="product", help="Manage the shared FinTS product registration.")
console = Console()


@app.command("update")
def update_product(
    plaintext_key: Annotated[
        str, typer.Argument(help="Plaintext product key material")
    ],
    product_version: Annotated[
        str, typer.Option("--product-version", help="Product version string")
    ],
) -> None:
    """Store a new product registration."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await UpdateProductRegistrationCommand.from_factory(
                    ctx.repo_factory,
                    ctx.service_factory,
                    product_version=product_version,
                )(plaintext_key)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(
            f"[green]Product registration updated.[/green] version={result.product_version}"
        )

    asyncio.run(_run())
