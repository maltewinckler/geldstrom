"""Shared constants for legacy FinTS behaviors."""

from fints.formals import BankIdentifier

ING_BANK_IDENTIFIER = BankIdentifier(country_identifier='280', bank_code='50010517')
SYSTEM_ID_UNASSIGNED = '0'

__all__ = ["ING_BANK_IDENTIFIER", "SYSTEM_ID_UNASSIGNED"]
