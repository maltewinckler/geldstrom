"""geldstrom-cli — five commands: health, accounts, balances, tan-methods, transactions."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from .client import GatewayClient, GatewayError
from .credentials import Creds, load_credentials
from .display import (
    print_accounts,
    print_balances,
    print_tan_methods,
    print_transactions,
)

app = typer.Typer(
    name="geldstrom-cli",
    help="Interactive developer CLI for manual testing of the geldstrom gateway.",
    no_args_is_help=True,
)
console = Console()

_EnvFile = Annotated[
    Path,
    typer.Option("--env-file", help=".env file path", show_default=True),
]
_GatewayUrl = Annotated[
    str | None,
    typer.Option("--gateway-url", help="Override GATEWAY_URL from env"),
]
_ApiKey = Annotated[
    str | None,
    typer.Option("--api-key", help="Override GATEWAY_API_KEY from env"),
]
_Blz = Annotated[str | None, typer.Option("--blz", help="Bank BLZ (8 digits)")]
_UserId = Annotated[str | None, typer.Option("--user-id", help="Bank user ID")]
_Password = Annotated[str | None, typer.Option("--password", help="Bank PIN/password")]
_TanMethod = Annotated[
    str | None, typer.Option("--tan-method", help="TAN method code (e.g. 946)")
]
_TanMedium = Annotated[
    str | None, typer.Option("--tan-medium", help="TAN medium / device name")
]


def _make_client(creds: Creds) -> GatewayClient:
    return GatewayClient(creds.gateway_url, creds.api_key)


def _resolve_creds(
    env_file: Path,
    gateway_url: str | None,
    api_key: str | None,
    blz: str | None,
    user_id: str | None,
    password: str | None,
    tan_method: str | None,
    tan_medium: str | None,
) -> Creds:
    return load_credentials(
        env_file,
        gateway_url=gateway_url,
        api_key=api_key,
        blz=blz,
        user_id=user_id,
        password=password,
        tan_method=tan_method,
        tan_medium=tan_medium,
    )


def _await_2fa(client: GatewayClient, body: dict) -> dict:
    """Handle a 202 response: print info, wait for approval, return result_payload."""
    op_id = body["operation_id"]
    expires_at = body["expires_at"]
    console.print(
        f"[bold yellow]⏳  2FA required[/bold yellow] — "
        f"approve on your device. Operation [dim]{op_id}[/dim]"
    )
    result = client.wait_for_operation(op_id, expires_at, console)
    status = result["status"]

    if status == "completed":
        return result.get("result_payload") or {}

    if status == "failed":
        reason = result.get("failure_reason") or "unknown"
        console.print(f"[red]Operation failed:[/red] {reason}")
        raise typer.Exit(1)

    # expired
    console.print("[red]Operation expired before 2FA was confirmed.[/red]")
    raise typer.Exit(1)


@app.command()
def health(
    gateway_url: _GatewayUrl = None,
    env_file: _EnvFile = Path(".env"),
) -> None:
    """Check gateway liveness (no credentials needed)."""
    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    url = gateway_url or os.getenv("GATEWAY_URL", "http://localhost:8000")
    try:
        with GatewayClient(url, "") as client:
            data = client.health()
        console.print(
            Panel(
                f"[green]✓ Gateway is alive[/green]  "
                f"status=[bold]{data.get('status', 'ok')}[/bold]",
                title="Health",
            )
        )
    except Exception as exc:
        console.print(f"[red]Gateway unreachable:[/red] {exc}")
        raise typer.Exit(1)  # noqa: B904


@app.command()
def accounts(
    env_file: _EnvFile = Path(".env"),
    gateway_url: _GatewayUrl = None,
    api_key: _ApiKey = None,
    blz: _Blz = None,
    user_id: _UserId = None,
    password: _Password = None,
    tan_method: _TanMethod = None,
    tan_medium: _TanMedium = None,
) -> None:
    """List bank accounts."""
    creds = _resolve_creds(
        env_file, gateway_url, api_key, blz, user_id, password, tan_method, tan_medium
    )
    try:
        with _make_client(creds) as client:
            status_code, body = client.accounts(creds)
            if status_code == 202:
                payload = _await_2fa(client, body)
                acct_list = payload.get("accounts", [])
            else:
                acct_list = body.get("accounts", [])
        print_accounts(console, acct_list)
    except GatewayError as exc:
        console.print(f"[red]Error {exc.status_code}:[/red] {exc.detail}")
        raise typer.Exit(1)  # noqa: B904


@app.command(name="tan-methods")
def tan_methods(
    env_file: _EnvFile = Path(".env"),
    gateway_url: _GatewayUrl = None,
    api_key: _ApiKey = None,
    blz: _Blz = None,
    user_id: _UserId = None,
    password: _Password = None,
    tan_method: _TanMethod = None,
    tan_medium: _TanMedium = None,
) -> None:
    """List available (decoupled) TAN methods for the bank account."""
    creds = _resolve_creds(
        env_file, gateway_url, api_key, blz, user_id, password, tan_method, tan_medium
    )
    try:
        with _make_client(creds) as client:
            status_code, body = client.tan_methods(creds)
            if status_code == 202:
                payload = _await_2fa(client, body)
                methods_list = payload.get("methods", [])
            else:
                methods_list = body.get("methods", [])
        print_tan_methods(console, methods_list)
    except GatewayError as exc:
        console.print(f"[red]Error {exc.status_code}:[/red] {exc.detail}")
        raise typer.Exit(1)  # noqa: B904


@app.command()
def balances(
    env_file: _EnvFile = Path(".env"),
    gateway_url: _GatewayUrl = None,
    api_key: _ApiKey = None,
    blz: _Blz = None,
    user_id: _UserId = None,
    password: _Password = None,
    tan_method: _TanMethod = None,
    tan_medium: _TanMedium = None,
) -> None:
    """Fetch current balances for all accounts."""
    creds = _resolve_creds(
        env_file, gateway_url, api_key, blz, user_id, password, tan_method, tan_medium
    )
    try:
        with _make_client(creds) as client:
            status_code, body = client.balances(creds)
            if status_code == 202:
                payload = _await_2fa(client, body)
                balances_list = payload.get("balances", [])
            else:
                balances_list = body.get("balances", [])
        print_balances(console, balances_list)
    except GatewayError as exc:
        console.print(f"[red]Error {exc.status_code}:[/red] {exc.detail}")
        raise typer.Exit(1)  # noqa: B904


@app.command()
def transactions(
    iban: Annotated[
        str | None,
        typer.Argument(help="IBAN to fetch transactions for (prompted if omitted)"),
    ] = None,
    days: Annotated[
        int,
        typer.Option("--days", help="Days back from today (default 30)"),
    ] = 30,
    start_date: Annotated[
        str | None,
        typer.Option("--start-date", help="Start date YYYY-MM-DD (overrides --days)"),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option("--end-date", help="End date YYYY-MM-DD (default: today)"),
    ] = None,
    env_file: _EnvFile = Path(".env"),
    gateway_url: _GatewayUrl = None,
    api_key: _ApiKey = None,
    blz: _Blz = None,
    user_id: _UserId = None,
    password: _Password = None,
    tan_method: _TanMethod = None,
    tan_medium: _TanMedium = None,
) -> None:
    """Fetch account transactions for a given IBAN."""
    if not iban:
        iban = typer.prompt("IBAN")
    creds = _resolve_creds(
        env_file, gateway_url, api_key, blz, user_id, password, tan_method, tan_medium
    )
    today = date.today()
    resolved_end = end_date or today.isoformat()
    resolved_start = start_date or (today - timedelta(days=days)).isoformat()

    try:
        with _make_client(creds) as client:
            status_code, body = client.transactions(
                creds, iban, resolved_start, resolved_end
            )
            if status_code == 202:
                payload = _await_2fa(client, body)
                tx_list = payload.get("transactions", [])
            else:
                tx_list = body.get("transactions", [])
        print_transactions(console, tx_list)
    except GatewayError as exc:
        console.print(f"[red]Error {exc.status_code}:[/red] {exc.detail}")
        raise typer.Exit(1)  # noqa: B904
