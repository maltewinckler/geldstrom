"""Fetch all balances in one batch call.

Usage:
    python examples/fetch_all_balances.py [--env-file .env] [-v]

Demonstrates the get_balances() method which fetches balances
for multiple accounts efficiently in a single request.
"""

from __future__ import annotations

import argparse

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_header,
    print_separator,
    setup_logging,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch all balances")
    add_common_args(parser)
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    print(f"Connecting to bank {env.get('FINTS_BLZ')}...")

    with create_client(env) as client:
        accounts = client.list_accounts()
        print(f"Found {len(accounts)} account(s)\n")

        # Fetch all balances at once
        balances = client.get_balances()

        print_header("ACCOUNT BALANCES")

        total = 0.0
        for balance in balances:
            # Find matching account for display
            iban = balance.account_id
            for acc in accounts:
                if acc.account_id == balance.account_id:
                    iban = acc.iban or acc.account_id
                    break

            amount = float(balance.booked.amount)
            total += amount

            print(f"\n  {iban}")
            print(
                f"  Balance: {balance.booked.amount:>12,.2f} {balance.booked.currency}"
            )
            if balance.available:
                print(
                    f"  Available:{balance.available.amount:>12,.2f} {balance.available.currency}"
                )
            print(f"  As of:   {balance.as_of.strftime('%Y-%m-%d %H:%M')}")

        print_separator()
        print(f"  TOTAL:   {total:>12,.2f} EUR")
        print()


if __name__ == "__main__":
    main()
