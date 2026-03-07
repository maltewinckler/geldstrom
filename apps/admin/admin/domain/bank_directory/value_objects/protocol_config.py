"""Protocol-specific configuration value objects."""

from pydantic import BaseModel, SecretStr


class FinTSConfig(BaseModel, frozen=True):
    """FinTS-specific configuration."""

    product_id: SecretStr
    product_version: str
    country_code: str = "DE"


# Union type for extensibility
# Will become Union[FinTSConfig, EBICSConfig, ...] later
ProtocolConfig = FinTSConfig
