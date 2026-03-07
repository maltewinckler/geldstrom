"""API schemas for the bank_directory bounded context."""

from pydantic import AnyHttpUrl, BaseModel, Field

from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol


class FinTSConfigRequest(BaseModel):
    """Request body for FinTS protocol configuration."""

    product_id: str
    product_version: str
    country_code: str = "DE"


class BankEndpointRequest(BaseModel):
    """Request body for creating or updating a bank endpoint."""

    bank_code: str = Field(min_length=1, max_length=20)
    protocol: BankingProtocol
    server_url: AnyHttpUrl
    protocol_config: FinTSConfigRequest  # Will become Union for multiple protocols
    metadata: dict | None = None


class BankEndpointResponse(BaseModel):
    """Response body for bank endpoint retrieval.

    Contains redacted protocol_config (no secrets).
    """

    bank_code: str
    protocol: BankingProtocol
    server_url: str
    metadata: dict | None = None
