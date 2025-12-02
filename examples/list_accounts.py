"""List all accounts.

Usage:
    python examples/list_accounts.py [--env-file .env]

The simplest example - connects to the bank and lists all accounts.
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
    parser = argparse.ArgumentParser(description="List all accounts")
    add_common_args(parser)
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    print(f"Connecting to bank {env.get('FINTS_BLZ')}...")

    with create_client(env) as client:
        accounts = client.list_accounts()

        print_header(f"ACCOUNTS ({len(accounts)} found)")

        for account in accounts:
            print(f"\n  ID:       {account.account_id}")
            print(f"  IBAN:     {account.iban or 'N/A'}")
            print(f"  BIC:      {account.bic or 'N/A'}")
            print(f"  Currency: {account.currency}")
            print(f"  Owner:    {account.owner.name}")

        print()


if __name__ == "__main__":
    main()
