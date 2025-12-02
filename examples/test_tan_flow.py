"""Debug script to test the TAN (2FA) flow.

Usage:
    python examples/test_tan_flow.py [--env-file path]

This script specifically tests operations that require TAN approval:
1. Connect to the bank (may or may not require TAN)
2. List accounts (usually no TAN)
3. Fetch transactions (typically requires TAN)

For decoupled TAN (SecureGo, pushTAN), you'll receive a push notification.
Approve it in your banking app within 2 minutes.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import date, timedelta

# Configure verbose logging to see TAN flow
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

# Enable DEBUG for FinTS dialog to see poll attempts
logging.getLogger("geldstrom.infrastructure.fints.dialog.factory").setLevel(logging.DEBUG)

from geldstrom import (
    BankCredentials,
    BankRoute,
    FinTS3Client,
)
from geldstrom.infrastructure.fints import GatewayCredentials


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
    parser = argparse.ArgumentParser(description="Test TAN flow")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()

    env = load_env(Path(args.env_file))
    credentials = build_credentials(env)

    print("=" * 70)
    print("TAN FLOW TEST")
    print("=" * 70)
    print(f"\nBank: {credentials.route.bank_code}")
    print(f"TAN Method: {credentials.credentials.two_factor_method or 'Not set'}")
    print(f"TAN Medium: {credentials.credentials.two_factor_device or 'Not set'}")
    print()

    if credentials.credentials.two_factor_method:
        print("⚠️  Two-factor authentication is enabled.")
        print("    When fetching transactions, you will receive a push notification.")
        print("    IMPORTANT: Approve it in your banking app within 2 minutes!")
        print()

    print("-" * 70)

    # Step 1: Connect
    print("\n[1/3] Connecting to bank...")
    client = FinTS3Client(credentials)

    try:
        with client:
            accounts = client.list_accounts()
            print(f"      ✓ Connected! Found {len(accounts)} account(s)")

            # Step 2: List accounts (no TAN needed)
            print("\n[2/3] Listing accounts (no TAN required)...")
            for acc in accounts:
                print(f"      - {acc.account_id}: {acc.iban or 'No IBAN'}")
            print("      ✓ Account listing complete")

            # Step 3: Fetch transactions (TAN required)
            if not accounts:
                print("\n[3/3] Skipping transactions - no accounts")
                return

            print("\n[3/3] Fetching transactions (TAN may be required)...")
            print("      ⏳ If you receive a push notification, APPROVE IT NOW!")
            print()

            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=91)
                feed = client.get_transactions(
                    accounts[0].account_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                print(f"      ✓ Got {len(feed.entries)} transaction(s)")

                if feed.entries:
                    print("\n      Recent transactions:")
                    for entry in feed.entries[:5]:
                        print(
                            f"        {entry.booking_date}: "
                            f"{entry.amount:>10.2f} {entry.currency}  "
                            f"{(entry.purpose or 'No description')[:40]}"
                        )

            except TimeoutError as e:
                print(f"      ⏱️  TIMEOUT: {e}")
                print()
                print("      The bank's TAN request timed out. This happens when:")
                print("      - You didn't approve the push notification in time")
                print("      - The bank's TAN request expired")
                print()
                print("      Try again and approve faster!")
                sys.exit(1)

            except ValueError as e:
                print(f"      ❌ ERROR: {e}")
                sys.exit(1)

    except Exception as e:
        print(f"\n❌ Fatal error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✓ TAN flow test complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

