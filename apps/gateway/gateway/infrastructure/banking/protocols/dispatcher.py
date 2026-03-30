"""Explicit banking connector dispatch by external protocol."""

from __future__ import annotations

from gateway.application.common import UnsupportedProtocolError
from gateway.domain.banking_gateway import BankingConnector, BankProtocol


class BankingConnectorDispatcher:
    """Resolve the correct banking connector for a requested protocol."""

    def __init__(self, *, fints_connector: BankingConnector) -> None:
        self._connectors = {BankProtocol.FINTS: fints_connector}

    def get(self, protocol: BankProtocol) -> BankingConnector:
        try:
            return self._connectors[protocol]
        except KeyError as exc:
            raise UnsupportedProtocolError(
                f"Unsupported banking protocol: {protocol.value}"
            ) from exc
