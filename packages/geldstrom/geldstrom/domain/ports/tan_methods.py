"""Port for querying TAN authentication methods."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from geldstrom.domain.connection import SessionToken
from geldstrom.domain.model.tan import TANMethod


class TANMethodsPort(Protocol):
    """
    Abstract interface for querying available TAN methods.

    TAN methods are typically discovered during session initialization
    when the bank sends BPD (Bank Parameter Data) containing HITANS
    segments. However, implementations should support querying TAN methods
    without requiring full authentication (to solve the chicken-and-egg
    problem of needing to know TAN methods before choosing one).
    """

    def get_tan_methods(
        self,
        state: SessionToken | None = None,
    ) -> Sequence[TANMethod]:
        """
        Get available TAN methods from bank parameters.

        Args:
            state: Optional session state with cached BPD. If not provided
                   or BPD is empty, the implementation should fetch BPD
                   using a lightweight method that doesn't require 2FA.

        Returns:
            Sequence of available TAN methods
        """
        ...


__all__ = ["TANMethodsPort"]
