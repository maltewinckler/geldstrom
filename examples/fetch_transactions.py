"""Fetch transaction history.

Usage:
    python examples/fetch_transactions.py [--days N] [--account ID] [-v]

Fetches transactions for the specified account (or first account).
For banks with decoupled TAN, you may receive a push notification.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_header,
    print_separator,
    setup_logging,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch transactions")
    add_common_args(parser)
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to fetch (default: 30)",
    )
    parser.add_argument(
        "--account",
        help="Account ID to fetch (default: first account)",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)

    print_header("TRANSACTION FETCH")
    print(f"\nBank: {env.get('FINTS_BLZ')}")
    print(f"Date Range: {start_date} to {end_date} ({args.days} days)")

    if env.get("FINTS_TAN_METHOD"):
        print("\nNote: TAN may be required for transaction queries.")
        print("Approve the push notification if prompted.\n")

    print_separator()
    print("Connecting...")

    with create_client(env) as client:
        accounts = client.list_accounts()
        print(f"Connected. Found {len(accounts)} account(s).")

        # Select account
        account = None
        if args.account:
            try:
                account = client.get_account(args.account)
            except ValueError:
                print(f"\nError: Account '{args.account}' not found.")
                print("Available accounts:")
                for acc in accounts:
                    print(f"  - {acc.account_id}")
                return
        else:
            account = accounts[0] if accounts else None

        if not account:
            print("\nNo accounts available.")
            return

        print(f"\nFetching transactions for {account.iban or account.account_id}...")

        feed = client.get_transactions(account, start_date=start_date, end_date=end_date)

        print_header(f"TRANSACTIONS ({len(feed.entries)} found)")

        if not feed.entries:
            print("\nNo transactions in the specified date range.")
        else:
            total_in = 0.0
            total_out = 0.0

            for entry in feed.entries:
                if entry.amount >= 0:
                    amount_str = f"+{entry.amount:,.2f}"
                    total_in += float(entry.amount)
                else:
                    amount_str = f"{entry.amount:,.2f}"
                    total_out += float(entry.amount)

                purpose = entry.purpose[:50] + "..." if len(entry.purpose) > 50 else entry.purpose
                counterpart = entry.counterpart_name or "Unknown"

                print(f"\n  {entry.booking_date} | {amount_str:>12} {entry.currency}")
                print(f"  {counterpart}")
                print(f"  {purpose}")

            print_separator()
            print(f"  Total In:  +{total_in:>10,.2f} EUR")
            print(f"  Total Out: {total_out:>11,.2f} EUR")
            print(f"  Net:       {(total_in + total_out):>11,.2f} EUR")

        print()


if __name__ == "__main__":
    main()
