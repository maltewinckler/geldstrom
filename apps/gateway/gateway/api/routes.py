"""FastAPI route handlers for the Gateway API.

Provides a factory function ``create_router()`` that returns an APIRouter
with the following endpoints mounted:

- POST /v1/transactions/fetch — initial fetch or 2FA resume
- GET  /v1/system/version     — build provenance

Domain exceptions are mapped to HTTP status codes:
  SessionNotFoundError     → 404
  UnsupportedProtocolError → 422
  BankNotSupportedError    → 422
  TANRejectedError         → 422
  BankConnectionError      → 502
  ApiKeyValidationError    → 503
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import SecretStr

from gateway.api.schemas import (
    ChallengeSchema,
    ErrorDetail,
    ErrorResponse,
    FetchTransactionsResponse,
    TransactionSchema,
    VersionResponse,
)
from gateway.application.use_cases import FetchTransactionsUseCase
from gateway.domain.banking.value_objects.connection import (
    BankConnection,
    BankingProtocol,
)
from gateway.domain.banking.value_objects.transaction import DateRange, TransactionFetch
from gateway.domain.exceptions import (
    BankConnectionError,
    BankNotSupportedError,
    SessionNotFoundError,
    TANRejectedError,
    UnsupportedProtocolError,
)
from gateway.domain.session.ports.services import AuditEventPublisher
from gateway.domain.session.value_objects.audit import AuditEvent

_EXCEPTION_MAP: list[tuple[type[Exception], int, str]] = [
    (SessionNotFoundError, 404, "SESSION_NOT_FOUND"),
    (UnsupportedProtocolError, 422, "UNSUPPORTED_PROTOCOL"),
    (BankNotSupportedError, 422, "BANK_NOT_SUPPORTED"),
    (TANRejectedError, 422, "TAN_REJECTED"),
    (BankConnectionError, 502, "BANK_CONNECTION_ERROR"),
]


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def create_router(
    use_case: FetchTransactionsUseCase,
    audit_publisher: AuditEventPublisher,
    require_api_key: Any,
) -> APIRouter:
    """Build an APIRouter with transaction-fetch and version endpoints."""
    router = APIRouter()

    @router.post("/v1/transactions/fetch", response_model=None)
    async def fetch_transactions(
        request: Request,
        account_id: str = Depends(require_api_key),
    ) -> FetchTransactionsResponse | JSONResponse:
        body: dict = await request.json()
        protocol: BankingProtocol | None = None

        try:
            if "session_id" in body:
                session_id: str = body["session_id"]
                tan_response: str = body["tan_response"]
                result = await use_case.execute_resume(session_id, tan_response)
            else:
                bc_data = body["bank_connection"]
                protocol = BankingProtocol(bc_data["protocol"])
                connection = BankConnection(
                    protocol=protocol,
                    bank_code=bc_data["bank_code"],
                    username=SecretStr(bc_data["username"]),
                    pin=SecretStr(bc_data["pin"]),
                )
                dr_data = body["date_range"]
                date_range = DateRange(start=dr_data["start"], end=dr_data["end"])
                fetch = TransactionFetch(iban=body["iban"], date_range=date_range)
                result = await use_case.execute_initial(connection, fetch)
        except (KeyError, ValueError) as exc:
            return _error_response(
                422, "VALIDATION_ERROR", f"Invalid or missing request field: {exc}"
            )
        except tuple(exc_cls for exc_cls, _, _ in _EXCEPTION_MAP) as exc:
            for exc_cls, status, code in _EXCEPTION_MAP:
                if isinstance(exc, exc_cls):
                    return _error_response(status, code, str(exc))
            raise  # pragma: no cover

        transactions = None
        if result.transactions is not None:
            transactions = [
                TransactionSchema(
                    entry_id=t.entry_id,
                    booking_date=t.booking_date,
                    value_date=t.value_date,
                    amount=t.amount,
                    currency=t.currency,
                    purpose=t.purpose,
                    counterpart_name=t.counterpart_name,
                    counterpart_iban=t.counterpart_iban,
                    metadata=t.metadata,
                )
                for t in result.transactions
            ]

        challenge = None
        if result.challenge is not None:
            import base64

            media = result.challenge.media_data
            encoded_media = base64.b64encode(media) if media else None
            challenge = ChallengeSchema(
                session_id=result.challenge.session_id,
                type=result.challenge.type,
                media_data=encoded_media,
            )

        response = FetchTransactionsResponse(
            status=result.status.value,
            transactions=transactions,
            challenge=challenge,
        )

        audit_event = AuditEvent(
            timestamp=datetime.now(UTC),
            account_id=account_id,
            remote_ip=request.client.host if request.client else "unknown",
            request_type="/v1/transactions/fetch",
            protocol=protocol,
        )
        asyncio.create_task(audit_publisher.publish(audit_event))

        # Use Pydantic's JSON serializer which handles date, Decimal,
        # and bytes→base64 correctly.
        from starlette.responses import Response

        return Response(
            content=response.model_dump_json(exclude_none=True),
            media_type="application/json",
        )

    @router.get("/v1/system/version")
    async def get_version() -> VersionResponse:
        return VersionResponse(
            git_commit_hash=os.environ.get("GIT_COMMIT_HASH", "unknown"),
            docker_image_sha256=os.environ.get("DOCKER_IMAGE_SHA256", "unknown"),
        )

    return router
