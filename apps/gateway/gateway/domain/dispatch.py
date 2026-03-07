"""Protocol dispatcher — registry-based, open/closed.

New protocols register handlers without modifying dispatch logic.
Each handler is constructed with its ProtocolConfig at startup.
"""

from __future__ import annotations

from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.exceptions import UnsupportedProtocolError
from gateway.domain.ports import BankingClient


class ProtocolDispatcher:
    """Registry-based dispatcher. Open/closed — new protocols register without
    modifying dispatch logic. Each handler is constructed with its ProtocolConfig."""

    def __init__(self) -> None:
        self._handlers: dict[BankingProtocol, BankingClient] = {}

    def register(self, protocol: BankingProtocol, client: BankingClient) -> None:
        self._handlers[protocol] = client

    def get_client(self, protocol: BankingProtocol) -> BankingClient:
        client = self._handlers.get(protocol)
        if client is None:
            raise UnsupportedProtocolError(protocol)
        return client
