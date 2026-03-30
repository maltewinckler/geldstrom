"""Domain value objects for initiating payments."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentInstruction(BaseModel, frozen=True):
    """Canonical fields required to submit a SEPA-style transfer."""

    debtor_account_id: str
    creditor_name: str
    creditor_iban: str
    amount: Decimal
    currency: str
    purpose: str | None = None
    creditor_bic: str | None = None
    end_to_end_id: str | None = None
    metadata: Mapping[str, str] = {}


class PaymentConfirmation(BaseModel, frozen=True):
    """Result returned by a connector after receiving a payment."""

    instruction: PaymentInstruction
    confirmation_id: str
    completed_at: datetime | None = None
    metadata: Mapping[str, str] = {}
