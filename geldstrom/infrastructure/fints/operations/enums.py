"""Enumerations describing FinTS operation capabilities."""

from enum import Enum


class FinTSOperations(Enum):
    """Read-only operation identifiers for FinTS capability checking.

    Each value is the segment code (e.g., "HKSAL") used to check
    if a bank supports the operation via its BPD.
    """

    GET_BALANCE = "HKSAL"
    GET_TRANSACTIONS = "HKKAZ"
    GET_TRANSACTIONS_XML = "HKCAZ"
    GET_CREDIT_CARD_TRANSACTIONS = "DKKKU"
    GET_STATEMENT = "HKEKA"
    GET_STATEMENT_PDF = "HKEKP"
    GET_HOLDINGS = "HKWPD"
    GET_SEPA_ACCOUNTS = "HKSPA"
    GET_SCHEDULED_DEBITS = "HKDBS"
    GET_STATUS_PROTOCOL = "HKPRO"


__all__ = ["FinTSOperations"]
