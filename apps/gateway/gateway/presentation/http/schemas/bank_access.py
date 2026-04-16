"""Shared bank-access request schema - credentials presented by consumers."""

from __future__ import annotations

from pydantic import BaseModel, SecretStr


class BankAccessRequest(BaseModel):
    """Credentials and routing needed for any bank operation."""

    model_config = {"extra": "forbid"}

    protocol: str
    blz: str
    user_id: str
    password: SecretStr
