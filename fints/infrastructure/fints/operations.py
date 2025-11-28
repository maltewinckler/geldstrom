"""Enumerations describing FinTS operation capabilities."""
from __future__ import annotations

from enum import Enum


class FinTSOperations(Enum):
    """Operation identifiers used in capability maps returned by FinTS banks."""

    GET_BALANCE = ("HKSAL",)
    GET_TRANSACTIONS = ("HKKAZ",)
    GET_TRANSACTIONS_XML = ("HKCAZ",)
    GET_CREDIT_CARD_TRANSACTIONS = ("DKKKU",)
    GET_STATEMENT = ("HKEKA",)
    GET_STATEMENT_PDF = ("HKEKP",)
    GET_HOLDINGS = ("HKWPD",)
    GET_SEPA_ACCOUNTS = ("HKSPA",)
    GET_SCHEDULED_DEBITS_SINGLE = ("HKDBS",)
    GET_SCHEDULED_DEBITS_MULTIPLE = ("HKDMB",)
    GET_STATUS_PROTOCOL = ("HKPRO",)
    SEPA_TRANSFER_SINGLE = ("HKCCS",)
    SEPA_TRANSFER_MULTIPLE = ("HKCCM",)
    SEPA_DEBIT_SINGLE = ("HKDSE",)
    SEPA_DEBIT_MULTIPLE = ("HKDME",)
    SEPA_DEBIT_SINGLE_COR1 = ("HKDSC",)
    SEPA_DEBIT_MULTIPLE_COR1 = ("HKDMC",)
    SEPA_STANDING_DEBIT_SINGLE_CREATE = ("HKDDE",)
    GET_SEPA_STANDING_DEBITS_SINGLE = ("HKDDB",)
    SEPA_STANDING_DEBIT_SINGLE_DELETE = ("HKDDL",)


__all__ = ["FinTSOperations"]
