"""Lookup endpoint schema."""

from __future__ import annotations

from pydantic import BaseModel


class BankInfoResponse(BaseModel):
    model_config = {"extra": "forbid"}

    blz: str
    bic: str | None
    name: str
    organization: str | None
    is_fints_capable: bool
