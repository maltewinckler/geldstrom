"""Rich table formatters for gateway responses."""

from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table


def print_accounts(console: Console, accounts: list[dict[str, Any]]) -> None:
    if not accounts:
        console.print("[yellow]No accounts returned.[/yellow]")
        return
    table = Table(
        title=f"Accounts ({len(accounts)})",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("IBAN", style="cyan", no_wrap=True)
    table.add_column("Owner", style="white")
    table.add_column("BIC", style="dim")
    table.add_column("Currency", style="dim", justify="center")
    table.add_column("Product", style="dim")
    for acc in accounts:
        table.add_row(
            acc.get("iban") or "-",
            acc.get("owner_name") or "-",
            acc.get("bic") or "-",
            acc.get("currency") or "-",
            acc.get("product_name") or "-",
        )
    console.print(table)


def print_transactions(console: Console, transactions: list[dict[str, Any]]) -> None:
    if not transactions:
        console.print("[yellow]No transactions found.[/yellow]")
        return

    feed_start = transactions[0].get("feed_start_date", "?")
    feed_end = transactions[0].get("feed_end_date", "?")
    title = f"Transactions ({len(transactions)} entries, {feed_start} → {feed_end})"
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Booking", style="dim", no_wrap=True)
    table.add_column("Value", style="dim", no_wrap=True)
    table.add_column("Amount", justify="right", no_wrap=True)
    table.add_column("Counterpart", style="white", max_width=28)
    table.add_column("Purpose", style="dim", max_width=42)

    for tx in transactions:
        try:
            val = float(tx.get("amount", "0"))
            color = "green" if val >= 0 else "red"
            amount_str = f"[{color}]{val:+.2f} {tx.get('currency', '')}[/{color}]"
        except (ValueError, TypeError):
            amount_str = str(tx.get("amount", "-"))

        table.add_row(
            tx.get("booking_date") or "-",
            tx.get("value_date") or "-",
            amount_str,
            tx.get("counterpart_name") or "-",
            tx.get("purpose") or "-",
        )
    console.print(table)


def print_tan_methods(console: Console, methods: list[dict[str, Any]]) -> None:
    if not methods:
        console.print("[yellow]No TAN methods returned.[/yellow]")
        return
    table = Table(title=f"TAN Methods ({len(methods)})", box=box.ROUNDED)
    table.add_column("Method ID", style="cyan")
    table.add_column("Display Name", style="white")
    for m in methods:
        table.add_row(
            m.get("method_id") or "-",
            m.get("display_name") or "-",
        )
    console.print(table)


def print_balances(console: Console, balances: list[dict[str, Any]]) -> None:
    if not balances:
        console.print("[yellow]No balances returned.[/yellow]")
        return
    table = Table(
        title=f"Balances ({len(balances)} accounts)", box=box.ROUNDED, show_lines=True
    )
    table.add_column("Account", style="cyan", no_wrap=True)
    table.add_column("As Of", style="dim", no_wrap=True)
    table.add_column("Booked", justify="right", no_wrap=True)
    table.add_column("Pending", justify="right", no_wrap=True, style="dim")
    for b in balances:
        try:
            booked_val = float(b.get("booked_amount", "0"))
            color = "green" if booked_val >= 0 else "red"
            booked_str = (
                f"[{color}]{booked_val:+.2f} {b.get('booked_currency', '')}[/{color}]"
            )
        except (ValueError, TypeError):
            booked_str = str(b.get("booked_amount", "-"))

        pending_amount = b.get("pending_amount")
        if pending_amount is not None:
            try:
                pval = float(pending_amount)
                color = "green" if pval >= 0 else "red"
                pending_str = (
                    f"[{color}]{pval:+.2f} {b.get('pending_currency', '')}[/{color}]"
                )
            except (ValueError, TypeError):
                pending_str = str(pending_amount)
        else:
            pending_str = "-"

        as_of_raw = b.get("as_of") or ""
        as_of_str = as_of_raw[:10] if as_of_raw else "-"

        table.add_row(
            b.get("account_id") or "-",
            as_of_str,
            booked_str,
            pending_str,
        )
    console.print(table)
