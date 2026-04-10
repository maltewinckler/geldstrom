"""Banking operations status and polling routes."""

from __future__ import annotations

from typing import Any
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
from gateway.domain.banking_gateway import BankLeitzahl, OperationStatus, OperationType

from ..dependencies import ApiKey, Factory
from ..schemas.operations import (
    PollCompletedAccountsResponse,
    PollCompletedBalancesResponse,
    PollCompletedTanMethodsResponse,
    PollCompletedTransactionsResponse,
    PollFailedResponse,
    PollOperationRequest,
    PollPendingResponse,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


def _build_response(result: Any) -> dict[str, Any]:
    """Build the typed flat response dict from an application result."""
    op_type = result.operation_type
    op_id = result.operation_id
    status = result.status

    if status == OperationStatus.PENDING_CONFIRMATION:
        return PollPendingResponse(
            status=status,
            operation_type=op_type.value if op_type else "",
            operation_id=op_id,
            expires_at=result.expires_at,
        ).model_dump(mode="json")

    if status == OperationStatus.COMPLETED:
        payload = result.result_payload or {}
        if op_type == OperationType.ACCOUNTS:
            return PollCompletedAccountsResponse(
                status=status,
                operation_type="accounts",
                operation_id=op_id,
                accounts=payload.get("accounts", []),
            ).model_dump(mode="json")
        if op_type == OperationType.TRANSACTIONS:
            return PollCompletedTransactionsResponse(
                status=status,
                operation_type="transactions",
                operation_id=op_id,
                transactions=payload.get("transactions", []),
            ).model_dump(mode="json")
        if op_type == OperationType.BALANCES:
            return PollCompletedBalancesResponse(
                status=status,
                operation_type="balances",
                operation_id=op_id,
                balances=payload.get("balances", []),
            ).model_dump(mode="json")
        if op_type == OperationType.TAN_METHODS:
            return PollCompletedTanMethodsResponse(
                status=status,
                operation_type="tan_methods",
                operation_id=op_id,
                methods=payload.get("methods", []),
            ).model_dump(mode="json")
        # fallback — unknown operation type completed
        return {"status": status, "operation_type": op_type, "operation_id": op_id}

    # failed / expired
    return PollFailedResponse(
        status=status,
        operation_type=op_type.value if op_type else "",
        operation_id=op_id,
        failure_reason=getattr(result, "failure_reason", None),
    ).model_dump(mode="json")


@router.get("/operations/{operation_id}")
async def get_operation_status(
    operation_id: UUID,
    presented_api_key: ApiKey,
    factory: Factory,
) -> JSONResponse:
    result = await GetOperationStatusQuery.from_factory(factory)(
        str(operation_id), presented_api_key
    )
    status_code = 202 if result.status == OperationStatus.PENDING_CONFIRMATION else 200
    return JSONResponse(status_code=status_code, content=_build_response(result))


@router.post(
    "/operations/{operation_id}/poll",
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

    status_code = 202 if result.status == OperationStatus.PENDING_CONFIRMATION else 200
    return JSONResponse(status_code=status_code, content=_build_response(result))
