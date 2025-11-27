"""Minimal example demonstrating the new read-only FinTS client.

Usage:
    python examples/read_only_client_demo.py [--env-file path] [--reuse-session]

Environment variables stored in .env (default location) must provide the
credentials and product metadata used to open the FinTS dialog:

    FINTS_BLZ=12345678
    FINTS_COUNTRY=DE
    FINTS_USER=demo
    FINTS_PIN=12345
    FINTS_SERVER=https://bank.example/hbci
    FINTS_PRODUCT_ID=MYAPP
    FINTS_PRODUCT_VERSION=1.0.0
    # optional
    FINTS_CUSTOMER_ID=demo
    FINTS_TAN_MEDIUM=TAN-APP
    FINTS_TAN_METHOD=944

The script prints discovered accounts and fetches the balance + recent transactions
for the first account. It intentionally avoids storing session data persistently;
feel free to extend `persist_session`/`load_session` helpers for your environment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Mapping, Optional

from fints.application import GatewayCredentials
from fints.domain import BankRoute, SessionState
from fints.readonly import ReadOnlyFinTSClient

SESSION_FILE = Path(".session_state.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only FinTS client demo")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file containing FinTS credentials (default: .env)",
    )
    parser.add_argument(
        "--reuse-session",
        action="store_true",
        help="Load cached session state from .session_state.json",
    )
    parser.add_argument(
        "--save-session",
        action="store_true",
        help="Persist refreshed session state to .session_state.json",
    )
    return parser.parse_args()


def build_credentials(env: Mapping[str, str]) -> GatewayCredentials:
    country = env.get("FINTS_COUNTRY", "DE")
    blz = env_required(env, "FINTS_BLZ")

    return GatewayCredentials(
        route=BankRoute(country, blz),
        server_url=env_required(env, "FINTS_SERVER"),
        user_id=env_required(env, "FINTS_USER"),
        pin=env_required(env, "FINTS_PIN"),
        product_id=env_required(env, "FINTS_PRODUCT_ID"),
        product_version=env_required(env, "FINTS_PRODUCT_VERSION"),
        customer_id=env.get("FINTS_CUSTOMER_ID"),
        tan_medium=env.get("FINTS_TAN_MEDIUM"),
        tan_method=env.get("FINTS_TAN_METHOD"),
    )


def env_required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key)
    if not value:
        raise RuntimeError(f"Missing {key} in .env file")
    return value


def load_env(path: Path) -> Mapping[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Env file {path} not found")

    env: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = _strip_quotes(value.strip())

    # Allow overriding with actual environment variables for convenience.
    for key, value in os.environ.items():
        if key.startswith("FINTS_"):
            env[key] = value

    return env


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_session() -> Optional[SessionState]:
    if not SESSION_FILE.exists():
        return None
    data = json.loads(SESSION_FILE.read_text())
    return SessionState.from_dict(data)


def persist_session(state: SessionState) -> None:
    SESSION_FILE.write_text(json.dumps(state.to_dict(), indent=2))


def main() -> None:
    args = parse_args()
    env_values = load_env(Path(args.env_file))
    credentials = build_credentials(env_values)
    session_state = load_session() if args.reuse_session else None

    client = ReadOnlyFinTSClient(credentials, session_state=session_state)
    with client:
        accounts = client.list_accounts()
        print("Discovered accounts:")
        for account in accounts:
            identifier = account.iban or account.metadata.get("account_number")
            print(f"- {account.account_id} {identifier} ({account.currency})")

        if not accounts:
            print("No accounts returned. Exiting.")
            return

        first = accounts[0]
        balance = client.get_balance(first.account_id)
        print(
            f"\nBalance for {first.account_id}: "
            f"{balance.booked.amount} {balance.booked.currency}"
        )

        feed = client.get_transactions(first.account_id)
        print(f"\nTransactions ({len(feed.entries)} entries):")
        for entry in feed.entries[:10]:
            print(
                f"{entry.booking_date} {entry.amount} {entry.currency}"
                f" {entry.purpose[:60]}"
            )

        if args.save_session and client.session_state:
            persist_session(client.session_state)
            print(f"\nSaved session to {SESSION_FILE}")


if __name__ == "__main__":
    main()
