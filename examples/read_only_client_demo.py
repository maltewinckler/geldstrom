"""Full demo of read-only FinTS operations.

Usage:
    python examples/read_only_client_demo.py [--reuse-session] [--save-session]

This comprehensive demo:
1. Connects to the bank
2. Lists all accounts
3. Fetches balance for the first account
4. Fetches recent transactions

SESSION STATE NOTE:
    The --reuse-session and --save-session flags save/restore bank parameters
    (BPD/UPD) and system ID, which speeds up connection by skipping parameter
    negotiation. However, this does NOT bypass 2FA/TAN - German banks require
    fresh authentication for each dialog session and for sensitive operations.
    Session state helps with:
      - Faster connection (skip parameter sync)
      - Preserving system ID (avoid re-registration)
    It does NOT help with:
      - Bypassing 2FA (by design, for security)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from geldstrom import SessionToken
from geldstrom.infrastructure.fints import FinTSSessionState

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_header,
    print_separator,
    setup_logging,
)

SESSION_FILE = Path(".session_state.json")


def load_session() -> FinTSSessionState | None:
    """Load a previously saved session from disk."""
    if not SESSION_FILE.exists():
        return None
    data = json.loads(SESSION_FILE.read_text())
    return FinTSSessionState.from_dict(data)


def save_session(state: SessionToken) -> None:
    """Save session to disk for later reuse."""
    if isinstance(state, FinTSSessionState):
        SESSION_FILE.write_text(json.dumps(state.to_dict(), indent=2))
    else:
        SESSION_FILE.write_bytes(state.serialize())


def main() -> None:
    parser = argparse.ArgumentParser(description="Full read-only FinTS demo")
    add_common_args(parser)
    parser.add_argument(
        "--reuse-session",
        action="store_true",
        help="Load cached session state from .session_state.json",
    )
    parser.add_argument(
        "--save-session",
        action="store_true",
        help="Save session state to .session_state.json",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)
    session_state = load_session() if args.reuse_session else None

    print_header("FINTS CLIENT DEMO")
    print(f"\nBank: {env.get('FINTS_BLZ')}")
    print(f"User: {env.get('FINTS_USER')}")

    if session_state:
        print("Session: Reusing saved session state")
    else:
        print("Session: Starting fresh")

    print_separator()
    print("Connecting...")

    with create_client(env, session_state=session_state) as client:
        # List accounts
        accounts = client.list_accounts()
        print(f"Connected. Found {len(accounts)} account(s).\n")

        print_header("ACCOUNTS")
        for account in accounts:
            iban = account.iban or account.account_id
            print(f"  - {iban} ({account.currency})")

        if not accounts:
            print("No accounts available.")
            return

        # Get balance
        first = accounts[0]
        print_separator()
        print(f"Balance for {first.iban or first.account_id}:")

        balance = client.get_balance(first)
        print(f"  {balance.booked.amount:,.2f} {balance.booked.currency}")

        # Get transactions
        print_separator()
        print("Recent transactions:")

        feed = client.get_transactions(first)
        if not feed.entries:
            print("  No transactions found.")
        else:
            for entry in feed.entries[:10]:
                purpose = entry.purpose[:50] if entry.purpose else "No description"
                print(f"  {entry.booking_date} {entry.amount:>10,.2f} {entry.currency}  {purpose}")

        # Save session if requested
        if args.save_session and client.session_state:
            save_session(client.session_state)
            print(f"\nSession saved to {SESSION_FILE}")

        print()


if __name__ == "__main__":
    main()
