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

For legacy compatibility, the original FinTS3PinTanClient is still available
but is deprecated in favor of the new FinTS3Client.
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

# --- Legacy client (deprecated) ---
# Import lazily to avoid circular imports and show deprecation on use


def __getattr__(name: str):
    """Lazy import for deprecated FinTS3PinTanClient."""
    if name == "FinTS3PinTanClient":
        import warnings

        warnings.warn(
            "FinTS3PinTanClient is deprecated. Use FinTS3Client instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from fints.client import FinTS3PinTanClient

        return FinTS3PinTanClient

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Version
    "version",
    # Clients
    "FinTS3Client",
    "ReadOnlyFinTSClient",
    "ClientCredentials",
    # Legacy (deprecated)
    "FinTS3PinTanClient",
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
