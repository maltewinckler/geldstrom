"""Unit tests for ProtocolDispatcher."""

from __future__ import annotations

import pytest

from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.dispatch import ProtocolDispatcher
from gateway.domain.exceptions import UnsupportedProtocolError


class _FakeClient:
    """Minimal stub satisfying BankingClient structural typing."""

    async def fetch_transactions(self, connection, endpoint, fetch):
        return None  # pragma: no cover

    async def resume_with_tan(self, challenge, tan_response):
        return None  # pragma: no cover


class TestProtocolDispatcher:
    def test_register_and_get_client(self) -> None:
        dispatcher = ProtocolDispatcher()
        client = _FakeClient()
        dispatcher.register(BankingProtocol.FINTS, client)

        assert dispatcher.get_client(BankingProtocol.FINTS) is client

    def test_get_client_raises_for_unregistered_protocol(self) -> None:
        dispatcher = ProtocolDispatcher()

        with pytest.raises(UnsupportedProtocolError):
            dispatcher.get_client(BankingProtocol.FINTS)

    def test_register_overwrites_previous_handler(self) -> None:
        dispatcher = ProtocolDispatcher()
        first = _FakeClient()
        second = _FakeClient()

        dispatcher.register(BankingProtocol.FINTS, first)
        dispatcher.register(BankingProtocol.FINTS, second)

        assert dispatcher.get_client(BankingProtocol.FINTS) is second
