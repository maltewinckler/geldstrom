"""Python FinTS - A pure Python implementation of FinTS 3.0.

This package provides clients for interacting with German banks using
the FinTS (Financial Transaction Services) protocol.

Quick Start:
    from geldstrom import FinTS3Client, BankCredentials, BankRoute
    from geldstrom.clients import ClientCredentials

    creds = ClientCredentials(
        route=BankRoute("DE", "12345678"),
        server_url="https://banking.example.com/fints",
        credentials=BankCredentials(
            user_id="user123",
            secret="mypin",
        ),
        product_id="YOUR_PRODUCT_ID",
    )

    with FinTS3Client(creds) as client:
        for account in client.list_accounts():
            balance = client.get_balance(account)
            print(f"{account.iban}: {balance.booked.amount}")
"""

# --- Client exports (presentation layer) ---
# --- Application exports ---
from geldstrom.application import GatewayCredentials
from geldstrom.clients import (
    ClientCredentials,
    FinTS3Client,
    ReadOnlyFinTSClient,
)

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
    SessionHandle,
    SessionToken,
    TransactionEntry,
    TransactionFeed,
)

# Version
version = "0.0.0"
__version__ = version
__all__ = [
    # Version
    "version",
    # Clients
    "FinTS3Client",
    "ReadOnlyFinTSClient",
    "ClientCredentials",
    # Domain models
    "Account",
    "AccountCapabilities",
    "AccountOwner",
    "BalanceAmount",
    "BalanceSnapshot",
    "BankCapabilities",
    "BankCredentials",
    "BankRoute",
    "SessionHandle",
    "SessionToken",
    "TransactionEntry",
    "TransactionFeed",
    # Application
    "GatewayCredentials",
]
