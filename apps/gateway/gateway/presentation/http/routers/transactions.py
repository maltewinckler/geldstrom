"""Banking transactions route."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.application.banking.commands.fetch_transactions import (
    FetchTransactionsCommand,
    FetchTransactionsInput,
)
from gateway.domain.banking_gateway import BankLeitzahl, BankProtocol, OperationStatus

from ..dependencies import ApiKey, Factory
from ..schemas.transactions import (
    FetchTransactionsRequest,
    TransactionsCompletedResponse,
    TransactionsPendingResponse,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


@router.post(
    "/transactions",
    responses={
        200: {"model": TransactionsCompletedResponse},
        202: {"model": TransactionsPendingResponse},
    },
)
async def fetch_transactions(
    body: FetchTransactionsRequest,
    presented_api_key: ApiKey,
    factory: Factory,
) -> JSONResponse:
    command = FetchTransactionsInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl(body.blz),
        user_id=body.user_id,
        password=body.password.get_secret_value(),
        iban=body.iban,
        start_date=body.start_date,
        end_date=body.end_date,
        tan_method=body.tan_method,
        tan_medium=body.tan_medium,
    )
    result = await FetchTransactionsCommand.from_factory(factory)(
        command, presented_api_key
    )
    if result.status is OperationStatus.COMPLETED:
        return JSONResponse(
            status_code=200,
            content=TransactionsCompletedResponse(
                status=result.status,
                transactions=result.transactions,
            ).model_dump(),
        )
    return JSONResponse(
        status_code=202,
        content=TransactionsPendingResponse(
            status=result.status,
            operation_id=result.operation_id,
            expires_at=result.expires_at,
        ).model_dump(mode="json"),
    )
