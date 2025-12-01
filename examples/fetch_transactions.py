"""Fetch transaction history with verbose output.

Usage:
    python examples/fetch_transactions.py [--env-file path] [--days N] [--account ID]

This script:
1. Connects to the bank
2. Lists available accounts
3. Fetches transactions for the specified account (or first account)

For banks with decoupled TAN (SecureGo), you'll receive a push notification
to approve the operation. The script waits up to 120 seconds for approval.
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import date, timedelta
from pathlib import Path

# Configure logging to see TAN flow
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from fints import (
    BankCredentials,
    BankRoute,
    ReadOnlyFinTSClient,
)
from fints.application import GatewayCredentials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch account transactions")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env)",
    )
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
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Env file {path} not found")

    env: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value

    for key, value in os.environ.items():
        if key.startswith("FINTS_"):
            env[key] = value

    return env


def build_credentials(env: dict[str, str]) -> GatewayCredentials:
    def require(key: str) -> str:
        val = env.get(key)
        if not val:
            raise RuntimeError(f"Missing {key}")
        return val

    return GatewayCredentials(
        route=BankRoute(
            country_code=env.get("FINTS_COUNTRY", "DE"),
            bank_code=require("FINTS_BLZ"),
        ),
        server_url=require("FINTS_SERVER"),
        credentials=BankCredentials(
            user_id=require("FINTS_USER"),
            secret=require("FINTS_PIN"),
            customer_id=env.get("FINTS_CUSTOMER_ID"),
            two_factor_device=env.get("FINTS_TAN_MEDIUM"),
            two_factor_method=env.get("FINTS_TAN_METHOD"),
        ),
        product_id=require("FINTS_PRODUCT_ID"),
        product_version=require("FINTS_PRODUCT_VERSION"),
    )


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger("fints").setLevel(logging.DEBUG)

    env = load_env(Path(args.env_file))
    credentials = build_credentials(env)

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)

    print("=" * 70)
    print("FinTS Transaction Fetch Demo")
    print("=" * 70)
    print(f"\nBank: {credentials.route.bank_code}")
    print(f"User: {credentials.user_id}")
    print(f"Date Range: {start_date} to {end_date} ({args.days} days)")
    print(f"TAN Method: {credentials.credentials.two_factor_method or 'Not configured'}")

    if credentials.credentials.two_factor_method:
        print("\n⚠️  Decoupled TAN is enabled.")
        print("    You may receive a push notification to approve the request.")
        print("    Please approve it in your banking app.\n")

    print("-" * 70)
    print("Connecting to bank...")

    client = ReadOnlyFinTSClient(credentials)

    with client:
        accounts = client.list_accounts()
        print(f"✓ Connected! Found {len(accounts)} account(s)")

        # Select account
        account = None
        if args.account:
            for acc in accounts:
                if acc.account_id == args.account:
                    account = acc
                    break
            if not account:
                print(f"\n❌ Account {args.account} not found")
                print("Available accounts:")
                for acc in accounts:
                    print(f"  - {acc.account_id}")
                return
        else:
            account = accounts[0] if accounts else None

        if not account:
            print("\n❌ No accounts available")
            return

        iban = account.iban or account.metadata.get("account_number", "?")
        print(f"\nFetching transactions for {account.account_id} ({iban})...")
        print("This may take a moment and might require TAN approval...")

        feed = client.get_transactions(
            account.account_id,
            start_date=start_date,
            end_date=end_date,
        )

        print(f"\n✓ Retrieved {len(feed.entries)} transaction(s)")

        print("\n" + "=" * 70)
        print("TRANSACTIONS")
        print("=" * 70)

        if not feed.entries:
            print("\nNo transactions found in the specified date range.")
        else:
            total_in = 0
            total_out = 0

            for entry in feed.entries:
                # Format amount
                if entry.amount >= 0:
                    amount_str = f"+{entry.amount:,.2f} {entry.currency}"
                    total_in += entry.amount
                else:
                    amount_str = f"{entry.amount:,.2f} {entry.currency}"
                    total_out += entry.amount

                # Truncate purpose for display
                purpose = (entry.purpose[:50] + "...") if len(entry.purpose) > 50 else entry.purpose
                counterpart = entry.counterpart_name or "Unknown"

                print(f"\n  {entry.booking_date} | {amount_str:>20}")
                print(f"  {counterpart}")
                print(f"  {purpose}")

            print("\n" + "-" * 70)
            print(f"  Total In:  +{total_in:,.2f} EUR")
            print(f"  Total Out: {total_out:,.2f} EUR")
            print(f"  Net:       {(total_in + total_out):,.2f} EUR")

        print("\n" + "=" * 70)
        print("Done!")
        print("=" * 70)


if __name__ == "__main__":
    main()

