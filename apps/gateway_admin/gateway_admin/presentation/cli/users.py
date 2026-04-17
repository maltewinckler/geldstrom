"""Typer CLI commands for managing users (API consumers)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from gateway_admin.application.commands import (
    CreateUserCommand,
    DeleteUserCommand,
    DisableUserCommand,
    ReactivateUserCommand,
    RotateUserKeyCommand,
    UpdateUserCommand,
)
from gateway_admin.application.queries import ListUsersQuery
from gateway_admin.domain.errors import ValidationError
from gateway_admin.presentation.cli._common import build_context

app = typer.Typer(name="users", help="Manage API consumers.")
console = Console()


@app.command("list")
def list_users() -> None:
    """List all API consumers."""

    async def _run() -> None:
        async with build_context() as ctx:
            users = await ListUsersQuery.from_factory(ctx.repo_factory)()

        table = Table("ID", "Email", "Status", "Created", "Rotated")
        for user in users:
            table.add_row(
                user.user_id,
                user.email,
                user.status.value,
                str(user.created_at.date()),
                str(user.rotated_at.date()) if user.rotated_at else "-",
            )
        console.print(table)

    asyncio.run(_run())


@app.command("create")
def create_user(
    email: Annotated[str, typer.Argument(help="Email address for the new user")],
) -> None:
    """Create a new API consumer and print the raw key once."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await CreateUserCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(email)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(
            f"[green]Created:[/green] {result.user.email} ({result.user.user_id})"
        )
        console.print(
            f"[yellow]Raw API key (shown once):[/yellow] {result.raw_api_key}"
        )

    asyncio.run(_run())


@app.command("update")
def update_user(
    user_id: Annotated[str, typer.Argument(help="User UUID")],
    email: Annotated[str, typer.Option("--email", help="New email address")],
) -> None:
    """Update a user's email address."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await UpdateUserCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(user_id, email=email)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(f"[green]Updated:[/green] {result.email} ({result.user_id})")

    asyncio.run(_run())


@app.command("disable")
def disable_user(
    user_id: Annotated[str, typer.Argument(help="User UUID")],
) -> None:
    """Disable an API consumer."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await DisableUserCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(user_id)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(f"[yellow]Disabled:[/yellow] {result.email} ({result.user_id})")

    asyncio.run(_run())


@app.command("delete")
def delete_user(
    user_id: Annotated[str, typer.Argument(help="User UUID")],
    confirm: Annotated[
        bool, typer.Option("--confirm", help="Confirm deletion")
    ] = False,
) -> None:
    """Delete an API consumer (irreversible)."""
    if not confirm:
        typer.confirm("This will permanently delete the user. Continue?", abort=True)

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await DeleteUserCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(user_id)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(f"[red]Deleted:[/red] {result.email} ({result.user_id})")

    asyncio.run(_run())


@app.command("rotate-key")
def rotate_key(
    user_id: Annotated[str, typer.Argument(help="User UUID")],
) -> None:
    """Rotate the API key for a user and print the new raw key once."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await RotateUserKeyCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(user_id)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(f"[green]Rotated key for:[/green] {result.user.email}")
        console.print(
            f"[yellow]New raw API key (shown once):[/yellow] {result.raw_api_key}"
        )

    asyncio.run(_run())


@app.command("reactivate")
def reactivate_user(
    user_id: Annotated[str, typer.Argument(help="User UUID")],
) -> None:
    """Reactivate a disabled API consumer and issue a fresh API key."""

    async def _run() -> None:
        async with build_context() as ctx:
            try:
                result = await ReactivateUserCommand.from_factory(
                    ctx.repo_factory, ctx.service_factory
                )(user_id)
            except ValidationError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        console.print(
            f"[green]Reactivated:[/green] {result.user.email} ({result.user.user_id})"
        )
        console.print(
            f"[yellow]New raw API key (shown once):[/yellow] {result.raw_api_key}"
        )

    asyncio.run(_run())
