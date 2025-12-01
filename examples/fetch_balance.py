"""Simple balance fetch example with verbose output.

Usage:
    python examples/fetch_balance.py [--env-file path]

This script:
1. Connects to the bank
2. Lists available accounts
3. Fetches balance for each account

For banks with decoupled TAN (SecureGo), you'll receive a push notification
to approve the login. The script waits up to 120 seconds for approval.
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

# Configure logging to see TAN flow
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from geldstrom import (
    BankCredentials,
    BankRoute,
    ReadOnlyFinTSClient,
)
from geldstrom.application import GatewayCredentials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch account balances")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env)",
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

    # Allow OS env to override
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
        logging.getLogger("geldstrom").setLevel(logging.DEBUG)

    env = load_env(Path(args.env_file))
    credentials = build_credentials(env)

    print("=" * 60)
    print("FinTS Balance Fetch Demo")
    print("=" * 60)
    print(f"\nBank: {credentials.route.bank_code}")
    print(f"User: {credentials.user_id}")
    print(f"TAN Method: {credentials.credentials.two_factor_method or 'Not configured'}")
    print(f"TAN Medium: {credentials.credentials.two_factor_device or 'Not configured'}")

    if credentials.credentials.two_factor_method:
        print("\n⚠️  Decoupled TAN is enabled.")
        print("    You may receive a push notification to approve the login.")
        print("    Please approve it in your banking app.\n")

    print("-" * 60)
    print("Connecting to bank...")

    client = ReadOnlyFinTSClient(credentials)

    with client:
        accounts = client.list_accounts()
        print(f"\n✓ Connected! Found {len(accounts)} account(s)")

        print("\n" + "=" * 60)
        print("ACCOUNTS")
        print("=" * 60)

        for account in accounts:
            iban = account.iban or account.metadata.get("account_number", "?")
            print(f"\n  Account: {account.account_id}")
            print(f"  IBAN:    {iban}")
            print(f"  Currency: {account.currency}")

            try:
                balance = client.get_balance(account.account_id)
                print(f"  Balance:  {balance.booked.amount:,.2f} {balance.booked.currency}")
                if balance.available:
                    print(f"  Available: {balance.available.amount:,.2f} {balance.available.currency}")
            except Exception as e:
                print(f"  Balance: ❌ Could not fetch ({e})")

        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)


if __name__ == "__main__":
    main()

