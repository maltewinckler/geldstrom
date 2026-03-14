"""Banking operations status route."""

from __future__ import annotations

from fastapi import APIRouter

from gateway.application.banking.queries.get_operation_status import (
    GetOperationStatusQuery,
)

from ..dependencies import ApiKey, Factory
from ..schemas.operations import OperationStatusResponse

router = APIRouter(prefix="/v1/banking", tags=["banking"])


@router.get("/operations/{operation_id}", response_model=OperationStatusResponse)
async def get_operation_status(
    operation_id: str,
    presented_api_key: ApiKey,
    factory: Factory,
) -> OperationStatusResponse:
    result = await GetOperationStatusQuery.from_factory(factory)(operation_id, presented_api_key)
    return OperationStatusResponse(
        status=result.status,
        operation_id=result.operation_id,
        result_payload=result.result_payload,
        failure_reason=result.failure_reason,
        expires_at=result.expires_at,
    )
