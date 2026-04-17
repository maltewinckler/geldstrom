"""Anti-corruption layer around the Geldstrom FinTS client."""

from gateway.infrastructure.banking.geldstrom.connector import GeldstromBankingConnector

__all__ = ["GeldstromBankingConnector"]
