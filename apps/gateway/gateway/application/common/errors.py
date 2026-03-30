"""Stable application error vocabulary for presentation layers."""

from __future__ import annotations

from enum import StrEnum


class GatewayErrorCode(StrEnum):
    """Stable error codes exposed by gateway use cases."""

    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    VALIDATION_ERROR = "validation_error"
    INSTITUTION_NOT_FOUND = "institution_not_found"
    OPERATION_NOT_FOUND = "operation_not_found"
    OPERATION_EXPIRED = "operation_expired"
    UNSUPPORTED_PROTOCOL = "unsupported_protocol"
    BANK_UPSTREAM_UNAVAILABLE = "bank_upstream_unavailable"
    INTERNAL_ERROR = "internal_error"


class ApplicationError(Exception):
    """Base exception carrying a stable gateway error code."""

    default_code = GatewayErrorCode.INTERNAL_ERROR

    def __init__(self, message: str, *, code: GatewayErrorCode | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code


class UnauthorizedError(ApplicationError):
    default_code = GatewayErrorCode.UNAUTHORIZED


class ForbiddenError(ApplicationError):
    default_code = GatewayErrorCode.FORBIDDEN


class ValidationError(ApplicationError):
    default_code = GatewayErrorCode.VALIDATION_ERROR


class InstitutionNotFoundError(ApplicationError):
    default_code = GatewayErrorCode.INSTITUTION_NOT_FOUND


class OperationNotFoundError(ApplicationError):
    default_code = GatewayErrorCode.OPERATION_NOT_FOUND


class OperationExpiredError(ApplicationError):
    default_code = GatewayErrorCode.OPERATION_EXPIRED


class UnsupportedProtocolError(ApplicationError):
    default_code = GatewayErrorCode.UNSUPPORTED_PROTOCOL


class BankUpstreamUnavailableError(ApplicationError):
    default_code = GatewayErrorCode.BANK_UPSTREAM_UNAVAILABLE


class InternalError(ApplicationError):
    default_code = GatewayErrorCode.INTERNAL_ERROR
