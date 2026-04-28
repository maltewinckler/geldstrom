"""Bank lookup routes."""

from __future__ import annotations

from fastapi import APIRouter

from gateway.application.banking.queries.list_banks import ListBanksQuery
from gateway.application.banking.queries.lookup_bank import LookupBankQuery
from gateway.presentation.http.dependencies import ApiKey, Factory
from gateway.presentation.http.schemas.errors import ErrorResponse
from gateway.presentation.http.schemas.lookup import BankInfoResponse, BankListResponse

router = APIRouter(prefix="/v1", tags=["lookup"])


@router.get(
    "/lookup/{blz}",
    response_model=BankInfoResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def lookup_bank(
    blz: str, presented_api_key: ApiKey, factory: Factory
) -> BankInfoResponse:
    result = await LookupBankQuery.from_factory(factory)(blz, presented_api_key)
    return BankInfoResponse(**result.model_dump())


@router.get(
    "/lookup",
    response_model=BankListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def list_banks(presented_api_key: ApiKey, factory: Factory) -> BankListResponse:
    results = await ListBanksQuery.from_factory(factory)(presented_api_key)
    return BankListResponse(banks=[BankInfoResponse(**e.model_dump()) for e in results])
