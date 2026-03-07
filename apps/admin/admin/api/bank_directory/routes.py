"""API routes for the bank_directory bounded context."""

from fastapi import APIRouter, Depends, Response, status
from pydantic import SecretStr

from admin.api.auth import verify_token
from admin.api.bank_directory.schemas import (
    BankEndpointRequest,
    BankEndpointResponse,
)
from admin.application.bank_directory.use_cases import (
    CreateBankEndpoint,
    DeleteBankEndpoint,
    GetBankEndpoint,
    ListBankEndpoints,
    UpdateBankEndpoint,
)
from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig

router = APIRouter(
    prefix="/admin/bank-endpoints",
    tags=["bank_directory"],
    dependencies=[Depends(verify_token)],
)


def get_create_bank_endpoint() -> CreateBankEndpoint:
    """Dependency injection for CreateBankEndpoint use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_list_bank_endpoints() -> ListBankEndpoints:
    """Dependency injection for ListBankEndpoints use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_get_bank_endpoint() -> GetBankEndpoint:
    """Dependency injection for GetBankEndpoint use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_update_bank_endpoint() -> UpdateBankEndpoint:
    """Dependency injection for UpdateBankEndpoint use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_delete_bank_endpoint() -> DeleteBankEndpoint:
    """Dependency injection for DeleteBankEndpoint use case."""
    raise NotImplementedError("Must be overridden at app startup")


def _request_to_domain(request: BankEndpointRequest) -> BankEndpoint:
    """Convert API request to domain entity."""
    return BankEndpoint(
        bank_code=request.bank_code,
        protocol=request.protocol,
        server_url=str(request.server_url),
        protocol_config=FinTSConfig(
            product_id=SecretStr(request.protocol_config.product_id),
            product_version=request.protocol_config.product_version,
            country_code=request.protocol_config.country_code,
        ),
        metadata=request.metadata,
    )


def _domain_to_response(endpoint: BankEndpoint) -> BankEndpointResponse:
    """Convert domain entity to API response (redacted)."""
    return BankEndpointResponse(
        bank_code=endpoint.bank_code,
        protocol=endpoint.protocol,
        server_url=endpoint.server_url,
        metadata=endpoint.metadata,
    )


@router.post(
    "",
    response_model=BankEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bank_endpoint(
    request: BankEndpointRequest,
    use_case: CreateBankEndpoint = Depends(get_create_bank_endpoint),
) -> BankEndpointResponse:
    """Create a new bank endpoint."""
    endpoint = _request_to_domain(request)
    await use_case.execute(endpoint)
    return _domain_to_response(endpoint)


@router.get(
    "",
    response_model=list[BankEndpointResponse],
)
async def list_bank_endpoints(
    use_case: ListBankEndpoints = Depends(get_list_bank_endpoints),
) -> list[BankEndpointResponse]:
    """List all bank endpoints (with redacted protocol_config)."""
    endpoints = await use_case.execute()
    return [_domain_to_response(endpoint) for endpoint in endpoints]


@router.get(
    "/{bank_code}",
    response_model=BankEndpointResponse,
)
async def get_bank_endpoint(
    bank_code: str,
    use_case: GetBankEndpoint = Depends(get_get_bank_endpoint),
) -> BankEndpointResponse:
    """Retrieve a bank endpoint (with redacted protocol_config)."""
    endpoint = await use_case.execute(bank_code)
    return _domain_to_response(endpoint)


@router.put(
    "/{bank_code}",
    response_model=BankEndpointResponse,
)
async def update_bank_endpoint(
    bank_code: str,
    request: BankEndpointRequest,
    use_case: UpdateBankEndpoint = Depends(get_update_bank_endpoint),
) -> BankEndpointResponse:
    """Update an existing bank endpoint."""
    # Ensure the bank_code in the path matches the request body
    endpoint = BankEndpoint(
        bank_code=bank_code,
        protocol=request.protocol,
        server_url=str(request.server_url),
        protocol_config=FinTSConfig(
            product_id=SecretStr(request.protocol_config.product_id),
            product_version=request.protocol_config.product_version,
            country_code=request.protocol_config.country_code,
        ),
        metadata=request.metadata,
    )
    await use_case.execute(endpoint)
    return _domain_to_response(endpoint)


@router.delete(
    "/{bank_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bank_endpoint(
    bank_code: str,
    use_case: DeleteBankEndpoint = Depends(get_delete_bank_endpoint),
) -> Response:
    """Delete a bank endpoint."""
    await use_case.execute(bank_code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
