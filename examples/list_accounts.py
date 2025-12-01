"""Simplest possible example - just list accounts.

Usage:
    python examples/list_accounts.py

Required environment variables in .env:
    FINTS_BLZ=12345678
    FINTS_USER=username
    FINTS_PIN=password
    FINTS_SERVER=https://bank.example/fints
    FINTS_PRODUCT_ID=YOUR_PRODUCT_ID
    FINTS_PRODUCT_VERSION=1.0.0
"""
from __future__ import annotations

import os
from pathlib import Path

from geldstrom import BankCredentials, BankRoute, ReadOnlyFinTSClient
from geldstrom.application import GatewayCredentials


def load_env() -> dict[str, str]:
    """Load .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        raise FileNotFoundError("Create a .env file with your bank credentials")

    env: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")

    # OS env overrides file
    for key, value in os.environ.items():
        if key.startswith("FINTS_"):
            env[key] = value

    return env


def main() -> None:
    env = load_env()

    # Build credentials
    credentials = GatewayCredentials(
        route=BankRoute(
            country_code=env.get("FINTS_COUNTRY", "DE"),
            bank_code=env["FINTS_BLZ"],
        ),
        server_url=env["FINTS_SERVER"],
        credentials=BankCredentials(
            user_id=env["FINTS_USER"],
            secret=env["FINTS_PIN"],
            customer_id=env.get("FINTS_CUSTOMER_ID"),
            two_factor_device=env.get("FINTS_TAN_MEDIUM"),
            two_factor_method=env.get("FINTS_TAN_METHOD"),
        ),
        product_id=env["FINTS_PRODUCT_ID"],
        product_version=env["FINTS_PRODUCT_VERSION"],
    )

    # Connect and list accounts
    print(f"Connecting to bank {credentials.route.bank_code}...")

    with ReadOnlyFinTSClient(credentials) as client:
        accounts = client.list_accounts()

        print(f"\nFound {len(accounts)} account(s):\n")
        for account in accounts:
            print(f"  ID:       {account.account_id}")
            print(f"  IBAN:     {account.iban or 'N/A'}")
            print(f"  Currency: {account.currency}")
            print()


if __name__ == "__main__":
    main()

