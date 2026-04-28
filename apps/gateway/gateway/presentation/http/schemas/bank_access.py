"""Shared bank-access request schema - credentials presented by consumers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class BankAccessRequest(BaseModel):
    """Common credentials and routing fields required by all banking endpoints."""

    model_config = {"extra": "forbid"}

    protocol: Literal["fints"]
    blz: str = Field(min_length=8, max_length=8, pattern=r"^\d{8}$")
    user_id: str = Field(max_length=64)
    password: SecretStr
    tan_method: str | None = Field(default=None, max_length=64)
    tan_medium: str | None = Field(default=None, max_length=64)
