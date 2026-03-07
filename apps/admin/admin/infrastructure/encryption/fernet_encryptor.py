"""Fernet encryption implementation for protocol configs."""

import json

from cryptography.fernet import Fernet

from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import (
    FinTSConfig,
    ProtocolConfig,
)


class FernetConfigEncryptor:
    """Implements ConfigEncryptor using Fernet symmetric encryption.

    Uses AES-128-CBC with HMAC for authenticated encryption.
    """

    def __init__(self, key: bytes) -> None:
        """Initialize with a Fernet key.

        Args:
            key: A 32 url-safe base64-encoded bytes key.
        """
        self._fernet = Fernet(key)

    def encrypt(self, config: ProtocolConfig) -> bytes:
        """Encrypt a protocol config for storage.

        Args:
            config: The protocol configuration to encrypt.

        Returns:
            Fernet-encrypted bytes of the JSON-serialized config.
        """
        # Manually serialize to expose SecretStr values (they are masked by default)
        if isinstance(config, FinTSConfig):
            data = {
                "product_id": config.product_id.get_secret_value(),
                "product_version": config.product_version,
                "country_code": config.country_code,
            }
        else:
            raise ValueError(f"Unknown config type: {type(config)}")

        json_bytes = json.dumps(data).encode()
        return self._fernet.encrypt(json_bytes)

    def decrypt(self, data: bytes, protocol: BankingProtocol) -> ProtocolConfig:
        """Decrypt stored protocol config data.

        Args:
            data: Fernet-encrypted bytes.
            protocol: The banking protocol to determine config type.

        Returns:
            The decrypted protocol configuration.

        Raises:
            ValueError: If the protocol is unknown.
        """
        json_bytes = self._fernet.decrypt(data)
        if protocol == BankingProtocol.fints:
            return FinTSConfig.model_validate_json(json_bytes)
        raise ValueError(f"Unknown protocol: {protocol}")
