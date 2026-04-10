"""Bank lookup route."""

from __future__ import annotations

from fastapi import APIRouter

from gateway.application.banking.queries.lookup_bank import LookupBankQuery

from ..dependencies import Factory
from ..schemas.errors import ErrorResponse
from ..schemas.lookup import BankInfoResponse

router = APIRouter(prefix="/v1", tags=["lookup"])


@router.get(
    "/lookup/{blz}",
    response_model=BankInfoResponse,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def lookup_bank(blz: str, factory: Factory) -> BankInfoResponse:
    result = await LookupBankQuery.from_factory(factory)(blz)
    return BankInfoResponse(**result.model_dump())
