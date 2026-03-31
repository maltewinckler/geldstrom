"""Banking accounts route."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.application.banking.commands.list_accounts import (
    ListAccountsCommand,
    ListAccountsInput,
)
from gateway.domain.banking_gateway import BankLeitzahl, BankProtocol, OperationStatus

from ..dependencies import ApiKey, Factory
from ..schemas.accounts import (
    AccountsCompletedResponse,
    AccountsPendingResponse,
    ListAccountsRequest,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


@router.post(
    "/accounts",
    responses={
        200: {"model": AccountsCompletedResponse},
        202: {"model": AccountsPendingResponse},
    },
)
async def list_accounts(
    body: ListAccountsRequest,
    presented_api_key: ApiKey,
    factory: Factory,
) -> JSONResponse:
    command = ListAccountsInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl(body.blz),
        user_id=body.user_id,
        password=body.password.get_secret_value(),
        tan_method=body.tan_method,
        tan_medium=body.tan_medium,
    )
    result = await ListAccountsCommand.from_factory(factory)(command, presented_api_key)
    if result.status is OperationStatus.COMPLETED:
        return JSONResponse(
            status_code=200,
            content=AccountsCompletedResponse(
                status=result.status,
                accounts=result.accounts,
            ).model_dump(),
        )
    return JSONResponse(
        status_code=202,
        content=AccountsPendingResponse(
            status=result.status,
            operation_id=result.operation_id,
            expires_at=result.expires_at,
        ).model_dump(mode="json"),
    )
