"""Tests for geldstrom public API preservation after migration."""

import pytest

import geldstrom


@pytest.mark.parametrize("symbol", geldstrom.__all__)
def test_public_api_symbol_importable(symbol: str) -> None:
    """Every symbol in geldstrom.__all__ is importable and non-None."""
    obj = getattr(geldstrom, symbol, None)
    assert obj is not None, f"geldstrom.{symbol} is None or missing"
