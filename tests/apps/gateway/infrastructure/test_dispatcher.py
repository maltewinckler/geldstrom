"""Tests for banking connector protocol dispatch."""

from gateway.domain.shared import BankProtocol
from gateway.infrastructure.banking.protocols import BankingConnectorDispatcher


def test_dispatcher_returns_fints_connector() -> None:
    connector = object()
    dispatcher = BankingConnectorDispatcher(fints_connector=connector)  # type: ignore[arg-type]

    assert dispatcher.get(BankProtocol.FINTS) is connector
