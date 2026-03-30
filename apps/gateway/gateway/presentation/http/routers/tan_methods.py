"""Banking TAN methods route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.application.banking.commands.get_tan_methods import (
    GetTanMethodsCommand,
    GetTanMethodsInput,
)
from gateway.domain.banking_gateway import BankProtocol, OperationStatus

from ..dependencies import ApiKey, Factory
from ..schemas.tan_methods import (
    GetTanMethodsRequest,
    TanMethodsCompletedResponse,
    TanMethodsPendingResponse,
)

router = APIRouter(prefix="/v1/banking", tags=["banking"])


@router.post(
    "/tan-methods",
    responses={
        200: {"model": TanMethodsCompletedResponse},
        202: {"model": TanMethodsPendingResponse},
    },
)
async def get_tan_methods(
    body: GetTanMethodsRequest,
    presented_api_key: ApiKey,
    factory: Factory,
) -> JSONResponse:
    command = GetTanMethodsInput(
        protocol=BankProtocol(body.protocol),
        blz=body.blz,
        user_id=body.user_id,
        password=body.password.get_secret_value(),
        tan_method=body.tan_method,
        tan_medium=body.tan_medium,
    )
    result = await GetTanMethodsCommand.from_factory(factory)(
        command, presented_api_key
    )
    if result.status is OperationStatus.COMPLETED:
        methods: list[dict[str, Any]] = [
            {"method_id": m.method_id, "display_name": m.display_name}
            for m in result.methods
        ]
        return JSONResponse(
            status_code=200,
            content=TanMethodsCompletedResponse(
                status=result.status,
                methods=methods,
            ).model_dump(),
        )
    return JSONResponse(
        status_code=202,
        content=TanMethodsPendingResponse(
            status=result.status,
            operation_id=result.operation_id,
            expires_at=result.expires_at,
        ).model_dump(mode="json"),
    )
