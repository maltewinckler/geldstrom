"""Tests for the BankLeitzahl value object."""

import pytest

from gateway.domain import DomainError
from gateway.domain.banking_gateway import (
    BankLeitzahl,
)


def test_bankleitzahl_rejects_invalid_values() -> None:
    with pytest.raises(DomainError, match="8-digit"):
        BankLeitzahl("123")
