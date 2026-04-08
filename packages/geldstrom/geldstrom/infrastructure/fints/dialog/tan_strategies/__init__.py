"""TAN handling strategies for FinTS dialog communication.

Two authentication paths:
- NoTanStrategy:        security_function=999, no HKTAN, direct response
- DecoupledTanStrategy: HKTAN injected, bank returns 3955, app-based approval
"""

from .base import TANStrategy
from .decoupled import DecoupledTanStrategy
from .no_tan import NoTanStrategy

__all__ = [
    "DecoupledTanStrategy",
    "NoTanStrategy",
    "TANStrategy",
]
