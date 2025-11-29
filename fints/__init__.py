"""Python FinTS - A pure Python implementation of FinTS 3.0.

This package provides clients for interacting with German banks using
the FinTS (Financial Transaction Services) protocol.

Quick Start:
    from fints import FinTS3Client, BankCredentials, BankRoute
    from fints.clients import ClientCredentials

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

# Version
version = "4.2.4"

# --- Client exports (presentation layer) ---
from fints.clients import (
    ClientCredentials,
    FinTS3Client,
    ReadOnlyFinTSClient,
)

# --- Domain exports ---
from fints.domain import (
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

# --- Application exports ---
from fints.application import GatewayCredentials

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
