"""Get a specific account by ID.

Usage:
    python examples/get_account.py [--account-id ID]

If no account ID is provided, lists all accounts with their IDs.
"""

from __future__ import annotations

import argparse

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_header,
    setup_logging,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Get account by ID")
    add_common_args(parser)
    parser.add_argument("--account-id", help="Account ID to fetch")
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    with create_client(env) as client:
        if args.account_id:
            try:
                account = client.get_account(args.account_id)
                print_header("ACCOUNT DETAILS")
                print(f"\n  ID:       {account.account_id}")
                print(f"  IBAN:     {account.iban or 'N/A'}")
                print(f"  BIC:      {account.bic or 'N/A'}")
                print(f"  Currency: {account.currency}")
                print(f"  Owner:    {account.owner.name}")
                print(f"\n  Capabilities:")
                print(f"    Balance:      {account.capabilities.can_fetch_balance}")
                print(f"    Transactions: {account.capabilities.can_list_transactions}")
                print(f"    Statements:   {account.capabilities.can_fetch_statements}")
                print()
            except ValueError as e:
                print(f"Error: {e}")
                print("\nAvailable account IDs:")
                for acc in client.list_accounts():
                    print(f"  - {acc.account_id}")
        else:
            print_header("AVAILABLE ACCOUNTS")
            for account in client.list_accounts():
                print(f"\n  {account.account_id}")
                print(f"    IBAN: {account.iban or 'N/A'}")
            print()


if __name__ == "__main__":
    main()
