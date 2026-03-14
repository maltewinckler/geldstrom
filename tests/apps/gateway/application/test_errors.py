"""Tests for application error codes."""

import pytest

from gateway.application.common import (
    ApplicationError,
    BankUpstreamUnavailableError,
    ForbiddenError,
    GatewayErrorCode,
    InstitutionNotFoundError,
    InternalError,
    OperationExpiredError,
    OperationNotFoundError,
    UnauthorizedError,
    UnsupportedProtocolError,
    ValidationError,
)


@pytest.mark.parametrize(
    ("error_type", "expected_code"),
    [
        (UnauthorizedError, GatewayErrorCode.UNAUTHORIZED),
        (ForbiddenError, GatewayErrorCode.FORBIDDEN),
        (ValidationError, GatewayErrorCode.VALIDATION_ERROR),
        (InstitutionNotFoundError, GatewayErrorCode.INSTITUTION_NOT_FOUND),
        (OperationNotFoundError, GatewayErrorCode.OPERATION_NOT_FOUND),
        (OperationExpiredError, GatewayErrorCode.OPERATION_EXPIRED),
        (UnsupportedProtocolError, GatewayErrorCode.UNSUPPORTED_PROTOCOL),
        (BankUpstreamUnavailableError, GatewayErrorCode.BANK_UPSTREAM_UNAVAILABLE),
        (InternalError, GatewayErrorCode.INTERNAL_ERROR),
    ],
)
def test_application_error_subclasses_expose_stable_codes(
    error_type, expected_code
) -> None:
    error = error_type("boom")

    assert error.code is expected_code
    assert str(error) == "boom"


def test_application_error_accepts_explicit_code_override() -> None:
    error = ApplicationError("boom", code=GatewayErrorCode.FORBIDDEN)

    assert error.code is GatewayErrorCode.FORBIDDEN
