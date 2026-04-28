"""Geldstrom - A pure Python implementation of FinTS 3.0.

This package provides clients for interacting with German banks using
the FinTS (Financial Transaction Services) protocol.

Quick Start:
    from geldstrom import FinTS3Client

    with FinTS3Client(
        bank_code="12345678",
        server_url="https://banking.example.com/fints",
        user_id="user123",
        pin="mypin",
        product_id="YOUR_PRODUCT_ID",
    ) as client:
        for account in client.list_accounts():
            balance = client.get_balance(account)
            print(f"{account.iban}: {balance.booked.amount}")

"""

from geldstrom.clients import FinTS3Client, FinTS3ClientDecoupled, PollResult

# --- Domain exports ---
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceAmount,
    BalanceSnapshot,
    BankCapabilities,
    BankCredentials,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)

# --- Infrastructure types re-exported for convenience ---
from geldstrom.infrastructure.fints.challenge import (
    Challenge,
    ChallengeData,
    ChallengeHandler,
    ChallengeResult,
    ChallengeType,
    DecoupledTANPending,
    TANConfig,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState, SessionToken
from geldstrom.infrastructure.fints.tan import TANMethod

# Version
version = "0.1.3"
__version__ = version
__all__ = [
    # Version
    "version",
    # Clients
    "FinTS3Client",
    "FinTS3ClientDecoupled",
    "PollResult",
    # Domain models
    "Account",
    "AccountCapabilities",
    "AccountOwner",
    "BalanceAmount",
    "BalanceSnapshot",
    "BankCapabilities",
    "BankCredentials",
    "BankRoute",
    "Challenge",
    "ChallengeData",
    "ChallengeHandler",
    "ChallengeResult",
    "ChallengeType",
    "DecoupledTANPending",
    "FinTSSessionState",
    "SessionToken",
    "TANConfig",
    "TANMethod",
    "TransactionEntry",
    "TransactionFeed",
]
