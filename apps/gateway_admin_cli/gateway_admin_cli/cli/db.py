"""Typer CLI commands for database management."""

from __future__ import annotations

import asyncio

import typer
from gateway_contracts.schema import metadata
from rich.console import Console
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from gateway_admin_cli.application.commands import UpdateProductRegistrationCommand
from gateway_admin_cli.config import get_settings

from ._common import build_factory

app = typer.Typer(name="db", help="Manage the database schema.")
console = Console()


def _quote_ident(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def _quote_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


@app.command("init")
def init_db() -> None:
    """Create the database, tables, and gateway DB user if they do not exist (idempotent)."""

    async def _run() -> None:
        s = get_settings()

        # Create the database if missing
        engine = create_async_engine(s.maintenance_url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                exists = await conn.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": s.postgres_db},
                )
            if exists:
                console.print(f"[dim]Database '{s.postgres_db}' already exists.[/dim]")
            else:
                async with engine.connect() as conn:
                    await conn.execute(
                        text(f"CREATE DATABASE {_quote_ident(s.postgres_db)}")
                    )
                console.print(f"[green]Created database '{s.postgres_db}'.[/green]")
        finally:
            await engine.dispose()

        # Create tables, gateway user, and grants
        engine = create_async_engine(s.database_url)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(metadata.create_all, checkfirst=True)

                gw_user = s.gateway_db_user
                gw_pw = s.gateway_db_password.get_secret_value()
                qi = _quote_ident(gw_user)

                user_exists = await conn.scalar(
                    text("SELECT 1 FROM pg_roles WHERE rolname = :n"),
                    {"n": gw_user},
                )
                if user_exists:
                    console.print(
                        f"[dim]Gateway DB user '{gw_user}' already exists.[/dim]"
                    )
                else:
                    await conn.execute(
                        text(
                            f"CREATE ROLE {qi} WITH LOGIN PASSWORD {_quote_literal(gw_pw)}"
                        )
                    )
                    console.print(
                        f"[green]Created gateway DB user '{gw_user}'.[/green]"
                    )

                await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {qi}"))
                await conn.execute(
                    text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {qi}")
                )
                await conn.execute(
                    text(
                        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public"
                        f" GRANT SELECT ON TABLES TO {qi}"
                    )
                )
        finally:
            await engine.dispose()

        tables = ", ".join(sorted(metadata.tables))
        console.print(f"[green]Tables ready:[/green] {tables}")

        async with build_factory() as factory:
            result = await UpdateProductRegistrationCommand.from_factory(
                factory,
                product_version=s.fints_product_version,
            )(s.fints_product_registration_key)
        console.print(
            f"[green]Product registration ready.[/green] "
            f"version={result.product_version}"
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

        tables = ", ".join(t.name for t in reversed(metadata.sorted_tables))
        console.print(f"[green]All records deleted from:[/green] {tables}")

    asyncio.run(_run())
