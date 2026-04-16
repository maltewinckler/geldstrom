"""Re-export shim: gateway_admin.domain.institutes."""

from gateway_admin.domain.entities.institutes import (
    FinTSInstitute,
    InstituteSelectionPolicy,
)
from gateway_admin.domain.value_objects.institutes import (
    BankLeitzahl,
    Bic,
    InstituteEndpoint,
)

__all__ = [
    "BankLeitzahl",
    "Bic",
    "FinTSInstitute",
    "InstituteEndpoint",
    "InstituteSelectionPolicy",
]
