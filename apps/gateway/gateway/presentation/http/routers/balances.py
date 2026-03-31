"""Banking balances route."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.application.banking.commands.get_balances import (
    GetBalancesCommand,
    GetBalancesInput,
)
from gateway.domain.banking_gateway import BankLeitzahl, BankProtocol, OperationStatus

from ..dependencies import ApiKey, Factory
from ..schemas.balances import (
    BalancesCompletedResponse,
    BalancesPendingResponse,
    GetBalancesRequest,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


@router.post(
    "/balances",
    responses={
        200: {"model": BalancesCompletedResponse},
        202: {"model": BalancesPendingResponse},
    },
)
async def get_balances(
    body: GetBalancesRequest,
    presented_api_key: ApiKey,
    factory: Factory,
) -> JSONResponse:
    command = GetBalancesInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl(body.blz),
        user_id=body.user_id,
        password=body.password.get_secret_value(),
        tan_method=body.tan_method,
        tan_medium=body.tan_medium,
    )
    result = await GetBalancesCommand.from_factory(factory)(command, presented_api_key)
    if result.status is OperationStatus.COMPLETED:
        return JSONResponse(
            status_code=200,
            content=BalancesCompletedResponse(
                status=result.status,
                balances=result.balances,
            ).model_dump(),
        )
    return JSONResponse(
        status_code=202,
        content=BalancesPendingResponse(
            status=result.status,
            operation_id=result.operation_id,
            expires_at=result.expires_at,
        ).model_dump(mode="json"),
    )
