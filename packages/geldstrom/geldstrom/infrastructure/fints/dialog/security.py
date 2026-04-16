"""Security mechanisms for FinTS dialog messages (signing and encryption)."""

from __future__ import annotations

import datetime
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from geldstrom.infrastructure.fints.protocol import (
    HNSHA2,
    HNSHK4,
    HNVSD1,
    HNVSK3,
    AlgorithmParameterIVName,
    AlgorithmParameterName,
    BankIdentifier,
    CompressionFunction,
    DateTimeType,
    EncryptionAlgorithm,
    EncryptionAlgorithmCoded,
    HashAlgorithm,
    IdentifiedRole,
    KeyName,
    KeyType,
    OperationMode,
    SecurityApplicationArea,
    SecurityDateTime,
    SecurityIdentificationDetails,
    SecurityMethod,
    SecurityProfile,
    SecurityRole,
    SignatureAlgorithm,
    UsageEncryption,
    UserDefinedSignature,
)

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog.message import FinTSMessage


@dataclass
class SecurityContext:
    """Security context for message signing/encryption."""

    bank_identifier: BankIdentifier
    user_id: str
    system_id: str


class StandaloneEncryptionMechanism:
    """PIN/TAN "encryption" mechanism for dialog messages.

    Wraps messages in the required HNVSK/HNVSD envelope structure.
    """

    def __init__(
        self, context: SecurityContext, security_method_version: int = 1
    ) -> None:
        self._context = context
        self.security_method_version = security_method_version

    def encrypt(self, message: FinTSMessage) -> None:
        """Wrap message in encryption envelope."""
        assert message.segments[0].header.type == "HNHBK"
        assert message.segments[-1].header.type == "HNHBS"

        plain_segments = message.segments[1:-1]
        del message.segments[1:-1]

        _now = datetime.datetime.now()

        message.segments.insert(
            1,
            HNVSK3(
                security_profile=SecurityProfile(
                    security_method=SecurityMethod.PIN,
                    security_method_version=self.security_method_version,
                ),
                security_function="998",
                security_role=SecurityRole.ISS,
                security_identification_details=SecurityIdentificationDetails(
                    identified_role=IdentifiedRole.MS,
                    identifier=self._context.system_id,
                ),
                security_datetime=SecurityDateTime(
                    date_time_type=DateTimeType.STS,
                    date=_now.date(),
                    time=_now.time(),
                ),
                encryption_algorithm=EncryptionAlgorithm(
                    usage_encryption=UsageEncryption.OSY,
                    operation_mode=OperationMode.CBC,
                    encryption_algorithm=EncryptionAlgorithmCoded.TWOKEY3DES,
                    algorithm_parameter_value=b"\x00" * 8,
                    algorithm_parameter_name=AlgorithmParameterName.KYE,
                    algorithm_parameter_iv_name=AlgorithmParameterIVName.IVC,
                ),
                key_name=KeyName(
                    bank_identifier=self._context.bank_identifier,
                    user_id=self._context.user_id,
                    key_type=KeyType.V,
                    key_number=0,
                    key_version=0,
                ),
                compression_function=CompressionFunction.NULL,
            ),
        )
        message.segments[1].header.number = 998

        from geldstrom.infrastructure.fints.protocol.parser import FinTSSerializer

        serializer = FinTSSerializer()
        data_bytes = serializer.serialize_message(plain_segments)
        message.segments.insert(
            2,
            HNVSD1(data=data_bytes),
        )
        message.segments[2].header.number = 999

    def decrypt(self, message: FinTSMessage) -> None:
        """No-op for PIN/TAN - messages are not actually encrypted."""
        pass


class StandaloneAuthenticationMechanism:
    """PIN/TAN authentication mechanism for dialog messages.

    Supports both one-step (security function 999) and two-step
    (custom security function) authentication.
    """

    def __init__(
        self,
        context: SecurityContext,
        pin: str,
        security_function: str = "999",
        tan_provider: callable = None,
    ) -> None:
        self._context = context
        self._pin = pin
        self.security_function = security_function
        self._tan_provider = tan_provider
        self._pending_signature = None

    def sign_prepare(self, message: FinTSMessage) -> None:
        """Add signature header to message."""
        _now = datetime.datetime.now()
        rand = random.SystemRandom()

        self._pending_signature = HNSHK4(
            security_profile=SecurityProfile(
                security_method=SecurityMethod.PIN,
                security_method_version=1,
            ),
            security_function=self.security_function,
            security_reference=str(rand.randint(1000000, 9999999)),
            security_application_area=SecurityApplicationArea.SHM,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                identified_role=IdentifiedRole.MS,
                identifier=self._context.system_id,
            ),
            security_reference_number=1,
            security_datetime=SecurityDateTime(
                date_time_type=DateTimeType.STS,
                date=_now.date(),
                time=_now.time(),
            ),
            hash_algorithm=HashAlgorithm(
                usage_hash="1",
                hash_algorithm="999",
                algorithm_parameter_name="1",
            ),
            signature_algorithm=SignatureAlgorithm(
                usage_signature="6",
                signature_algorithm="10",
                operation_mode="16",
            ),
            key_name=KeyName(
                bank_identifier=self._context.bank_identifier,
                user_id=self._context.user_id,
                key_type=KeyType.S,
                key_number=0,
                key_version=0,
            ),
        )

        message += self._pending_signature

    def sign_commit(self, message: FinTSMessage) -> None:
        """Complete signature with PIN and optional TAN."""
        if not self._pending_signature:
            raise RuntimeError("No signature is pending")

        if self._pending_signature not in message.segments:
            raise RuntimeError("Cannot sign a message that was not prepared")

        tan = None
        if self._tan_provider and self.security_function != "999":
            tan = self._tan_provider()

        signature = HNSHA2(
            security_reference=self._pending_signature.security_reference,
            user_defined_signature=UserDefinedSignature(
                pin=self._pin,
                tan=tan,
            ),
        )

        self._pending_signature = None
        message += signature

    def verify(self, message: FinTSMessage) -> None:
        """No-op - response verification not implemented."""
        pass


__all__ = [
    "SecurityContext",
    "StandaloneAuthenticationMechanism",
    "StandaloneEncryptionMechanism",
]
