"""Key validation gRPC servicer implementation."""

from grpc import StatusCode
from grpc.aio import ServicerContext
from sqlalchemy.exc import SQLAlchemyError

from admin.domain.api_keys.ports.repository import ApiKeyRepository
from admin.domain.api_keys.ports.services import KeyCache
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.infrastructure.grpc.generated.key_validation_pb2 import (
    KeyRequest,
    KeyResponse,
)
from admin.infrastructure.grpc.generated.key_validation_pb2_grpc import (
    KeyValidationServiceServicer,
)


class KeyValidationServicer(KeyValidationServiceServicer):
    """gRPC servicer for key validation.

    Checks cache first, falls back to database.
    """

    def __init__(
        self,
        key_cache: KeyCache,
        api_key_repo: ApiKeyRepository,
    ) -> None:
        """Initialize the servicer with cache and repository."""
        self._key_cache = key_cache
        self._api_key_repo = api_key_repo

    async def ValidateKey(
        self, request: KeyRequest, context: ServicerContext
    ) -> KeyResponse:
        """Validate an API key by its SHA-256 hash.

        1. Check cache first
        2. Fall back to database if not cached
        3. Populate cache on database hit
        """
        sha256_hash = SHA256KeyHash(value=request.key_hash)

        # 1. Check cache first
        account_id = await self._key_cache.get(sha256_hash)
        if account_id:
            return KeyResponse(is_valid=True, account_id=account_id)

        # 2. Fall back to database
        try:
            api_key = await self._api_key_repo.get_by_sha256_hash(sha256_hash)
            if api_key and api_key.status == KeyStatus.active:
                # Populate cache for next time
                await self._key_cache.set(sha256_hash, api_key.account_id)
                return KeyResponse(is_valid=True, account_id=str(api_key.account_id))
            return KeyResponse(is_valid=False, account_id="")
        except SQLAlchemyError:
            await context.abort(StatusCode.UNAVAILABLE, "database unavailable")
            # This line is never reached but satisfies type checker
            return KeyResponse(is_valid=False, account_id="")
