"""Banking operations status and polling routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.application.banking.commands.poll_operation import (
    PollOperationCommand,
    PollOperationInput,
)
from gateway.application.banking.queries.get_operation_status import (
    GetOperationStatusQuery,
)
from gateway.domain.banking_gateway import BankLeitzahl, OperationStatus

from ..dependencies import ApiKey, Factory
from ..schemas.operations import (
    OperationStatusResponse,
    PollOperationRequest,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


@router.get("/operations/{operation_id}", response_model=OperationStatusResponse)
async def get_operation_status(
    operation_id: UUID,
    presented_api_key: ApiKey,
    factory: Factory,
) -> OperationStatusResponse:
    result = await GetOperationStatusQuery.from_factory(factory)(
        str(operation_id), presented_api_key
    )
    return OperationStatusResponse(
        status=result.status,
        operation_id=result.operation_id,
        result_payload=result.result_payload,
        failure_reason=result.failure_reason,
        expires_at=result.expires_at,
    )


@router.post(
    "/operations/{operation_id}/poll",
    response_model=OperationStatusResponse,
    responses={
        200: {"description": "Operation completed or failed"},
        202: {"description": "TAN still pending — continue polling"},
    },
)
async def poll_operation(
    operation_id: UUID,
    body: PollOperationRequest,
    presented_api_key: ApiKey,
    factory: Factory,
) -> JSONResponse:
    command = PollOperationCommand.from_factory(factory)
    result = await command(
        str(operation_id),
        PollOperationInput(
            blz=BankLeitzahl(body.blz),
            user_id=body.user_id,
            password=body.password.get_secret_value(),
            tan_method=body.tan_method,
            tan_medium=body.tan_medium,
        ),
        presented_api_key,
    )

    status_code = 200
    if result.status == OperationStatus.PENDING_CONFIRMATION:
        status_code = 202

    return JSONResponse(
        status_code=status_code,
        content=OperationStatusResponse(
            status=result.status,
            operation_id=result.operation_id,
            result_payload=result.result_payload,
            failure_reason=result.failure_reason,
            expires_at=result.expires_at,
        ).model_dump(mode="json"),
    )
