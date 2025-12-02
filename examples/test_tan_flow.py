"""Test the TAN (2FA) flow.

Usage:
    python examples/test_tan_flow.py [--env-file .env]

This script specifically tests operations that require TAN approval:
1. Connect to the bank
2. List accounts (usually no TAN)
3. Fetch transactions (typically requires TAN for longer date ranges)

For decoupled TAN (SecureGo, pushTAN), approve the push notification
in your banking app within 2 minutes.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_footer,
    print_header,
    print_separator,
    setup_logging,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test TAN flow")
    add_common_args(parser)
    args = parser.parse_args()

    # Always enable verbose for TAN testing
    setup_logging(verbose=True)
    env = load_env(args.env_file)

    print_header("TAN FLOW TEST")
    print(f"\nBank: {env.get('FINTS_BLZ')}")
    print(f"TAN Method: {env.get('FINTS_TAN_METHOD') or 'Not configured'}")
    print(f"TAN Medium: {env.get('FINTS_TAN_MEDIUM') or 'Not configured'}")

    if env.get("FINTS_TAN_METHOD"):
        print("\nTwo-factor authentication is enabled.")
        print("When fetching transactions, you will receive a push notification.")
        print("IMPORTANT: Approve it in your banking app within 2 minutes!")

    print_separator()

    try:
        with create_client(env) as client:
            # Step 1: Connect
            print("\n[1/3] Connecting to bank...")
            accounts = client.list_accounts()
            print(f"      Connected. Found {len(accounts)} account(s).")

            # Step 2: List accounts
            print("\n[2/3] Listing accounts (no TAN required)...")
            for acc in accounts:
                print(f"      - {acc.account_id}: {acc.iban or 'No IBAN'}")
            print("      Done.")

            # Step 3: Fetch transactions (may require TAN)
            if not accounts:
                print("\n[3/3] Skipping transactions - no accounts")
                return

            print("\n[3/3] Fetching transactions (TAN may be required)...")
            print("      If you receive a push notification, APPROVE IT NOW!")
            print()

            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=91)
                feed = client.get_transactions(
                    accounts[0],
                    start_date=start_date,
                    end_date=end_date,
                )
                print(f"      Got {len(feed.entries)} transaction(s).")

                if feed.entries:
                    print("\n      Recent transactions:")
                    for entry in feed.entries[:5]:
                        purpose = (entry.purpose or "No description")[:40]
                        print(f"        {entry.booking_date}: {entry.amount:>10.2f} {entry.currency}  {purpose}")

            except TimeoutError as e:
                print(f"      TIMEOUT: {e}")
                print("\n      The TAN request timed out. This happens when:")
                print("      - You didn't approve the push notification in time")
                print("      - The bank's TAN request expired")
                print("\n      Try again and approve faster!")
                sys.exit(1)

            except ValueError as e:
                print(f"      ERROR: {e}")
                sys.exit(1)

    except Exception as e:
        print(f"\nFATAL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print_footer()
    print("TAN flow test complete!")
    print_footer()


if __name__ == "__main__":
    main()
