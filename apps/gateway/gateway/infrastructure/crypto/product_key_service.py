"""Encryption service for shared FinTS product keys."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from gateway.application.common import InternalError
from gateway.domain.product_registration import EncryptedProductKey


class ProductKeyService:
    """Encrypt and decrypt shared product key material."""

    def __init__(self, master_key: str | bytes) -> None:
        material = (
            master_key.encode("utf-8") if isinstance(master_key, str) else master_key
        )
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
        self._fernet = Fernet(derived_key)

    def encrypt(self, plaintext: str) -> EncryptedProductKey:
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return EncryptedProductKey(token)

    def decrypt(self, encrypted: EncryptedProductKey) -> str:
        try:
            plaintext = self._fernet.decrypt(encrypted.value)
        except InvalidToken as exc:
            raise InternalError(
                "Unable to decrypt product key with the configured master key"
            ) from exc
        return plaintext.decode("utf-8")
