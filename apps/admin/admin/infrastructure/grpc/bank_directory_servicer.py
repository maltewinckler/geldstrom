"""Bank directory gRPC servicer implementation."""

from grpc import StatusCode
from grpc.aio import ServicerContext
from sqlalchemy.exc import SQLAlchemyError

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.ports.repository import BankEndpointRepository
from admin.domain.bank_directory.ports.services import EndpointCache
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.infrastructure.grpc.generated.bank_directory_pb2 import (
    BankEndpointResponse,
    GetBankEndpointRequest,
)
from admin.infrastructure.grpc.generated.bank_directory_pb2_grpc import (
    BankDirectoryServiceServicer,
)


class BankDirectoryServicer(BankDirectoryServiceServicer):
    """gRPC servicer for bank directory lookups.

    Checks cache first, falls back to database.
    """

    def __init__(
        self,
        endpoint_cache: EndpointCache,
        bank_endpoint_repo: BankEndpointRepository,
    ) -> None:
        """Initialize the servicer with cache and repository."""
        self._endpoint_cache = endpoint_cache
        self._bank_endpoint_repo = bank_endpoint_repo

    async def GetBankEndpoint(
        self, request: GetBankEndpointRequest, context: ServicerContext
    ) -> BankEndpointResponse:
        """Get a bank endpoint by bank code.

        1. Check cache first
        2. Fall back to database if not cached
        3. Populate cache on database hit
        4. Return NOT_FOUND if missing
        """
        # 1. Check cache first
        cached = await self._endpoint_cache.get(request.bank_code)
        if cached:
            return self._to_response(cached)

        # 2. Fall back to database
        try:
            endpoint = await self._bank_endpoint_repo.get(request.bank_code)
            if endpoint:
                await self._endpoint_cache.set(endpoint)
                return self._to_response(endpoint)
            await context.abort(
                StatusCode.NOT_FOUND, f"bank_code {request.bank_code} not found"
            )
            # This line is never reached but satisfies type checker
            return BankEndpointResponse()
        except SQLAlchemyError:
            await context.abort(StatusCode.UNAVAILABLE, "database unavailable")
            # This line is never reached but satisfies type checker
            return BankEndpointResponse()

    def _to_response(self, endpoint: BankEndpoint) -> BankEndpointResponse:
        """Convert a BankEndpoint entity to a gRPC response."""
        config = endpoint.protocol_config
        return BankEndpointResponse(
            bank_code=endpoint.bank_code,
            protocol=endpoint.protocol.value,
            server_url=endpoint.server_url,
            fints_product_id=(
                config.product_id.get_secret_value()
                if isinstance(config, FinTSConfig)
                else ""
            ),
            fints_product_version=(
                config.product_version if isinstance(config, FinTSConfig) else ""
            ),
            fints_country_code=(
                config.country_code if isinstance(config, FinTSConfig) else ""
            ),
            metadata=endpoint.metadata or {},
        )
