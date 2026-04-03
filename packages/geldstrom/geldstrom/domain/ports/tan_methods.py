"""Port for querying TAN authentication methods."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from geldstrom.domain.connection import SessionToken
from geldstrom.domain.model.tan import TANMethod


class TANMethodsPort(Protocol):
    """Query available TAN methods from bank parameters."""

    def get_tan_methods(
        self,
        state: SessionToken | None = None,
    ) -> Sequence[TANMethod]: ...


__all__ = ["TANMethodsPort"]
