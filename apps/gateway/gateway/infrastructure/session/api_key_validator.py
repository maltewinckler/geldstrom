"""API key validator using Admin gRPC ValidateKey.

Implements the ApiKeyValidator port. On each validate() call:
1. SHA-256 hash the raw API key
2. Call gRPC ValidateKey(KeyRequest(key_hash=hash))
3. Return ApiKeyValidationResult based on gRPC response
4. On gRPC error → raise ApiKeyValidationError (caller maps to HTTP 503)

No caching — Admin service maintains its own internal cache.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import grpc

from gateway.domain.session.value_objects.audit import ApiKeyValidationResult
from gateway.infrastructure.grpc.generated import key_validation_pb2
from gateway.infrastructure.grpc.generated.key_validation_pb2_grpc import (
    KeyValidationServiceStub,
)

if TYPE_CHECKING:
    from grpc.aio import Channel


class ApiKeyValidationError(Exception):
    """Raised when the API key validation backend (gRPC) is unavailable."""

    def __init__(self, reason: str | None = None) -> None:
        self.reason = reason
        msg = "API key validation service unavailable"
        if reason:
            msg = f"{msg}: {reason}"
        super().__init__(msg)


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


class GrpcApiKeyValidator:
    """Implements ApiKeyValidator port using Admin gRPC ValidateKey.

    Calls Admin gRPC on every request — no local caching.
    Admin maintains its own internal cache for fast validation.
    """

    def __init__(self, channel: Channel) -> None:
        self._stub = KeyValidationServiceStub(channel)

    async def validate(self, api_key: str) -> ApiKeyValidationResult:
        """Validate an API key via Admin gRPC ValidateKey."""
        key_hash = _hash_api_key(api_key)

        try:
            request = key_validation_pb2.KeyRequest(key_hash=key_hash)
            response = await self._stub.ValidateKey(request)
        except grpc.RpcError as exc:
            raise ApiKeyValidationError(reason=str(exc)) from exc
        except Exception as exc:
            raise ApiKeyValidationError(reason=str(exc)) from exc

        return ApiKeyValidationResult(
            is_valid=response.is_valid,
            account_id=response.account_id if response.account_id else None,
            metadata=None,
        )
