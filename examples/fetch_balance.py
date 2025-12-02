"""Fetch balance for each account.

Usage:
    python examples/fetch_balance.py [--env-file .env] [-v]

Connects to the bank and fetches the current balance for all accounts.
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
    parser = argparse.ArgumentParser(description="Fetch account balances")
    add_common_args(parser)
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    print_header("BALANCE FETCH")
    print(f"\nBank: {env.get('FINTS_BLZ')}")
    print(f"User: {env.get('FINTS_USER')}")

    if env.get("FINTS_TAN_METHOD"):
        print("\nNote: Decoupled TAN is enabled.")
        print("You may receive a push notification to approve.\n")

    print_separator()
    print("Connecting...")

    with create_client(env) as client:
        accounts = client.list_accounts()
        print(f"Connected. Found {len(accounts)} account(s).\n")

        print_header("ACCOUNTS & BALANCES")

        for account in accounts:
            iban = account.iban or account.account_id
            print(f"\n  Account: {iban}")
            print(f"  Currency: {account.currency}")

            try:
                balance = client.get_balance(account)
                print(
                    f"  Balance:  {balance.booked.amount:>12,.2f} {balance.booked.currency}"
                )
                if balance.available:
                    print(
                        f"  Available:{balance.available.amount:>12,.2f} {balance.available.currency}"
                    )
            except Exception as e:
                print(f"  Balance:  Error - {e}")

        print()


if __name__ == "__main__":
    main()
