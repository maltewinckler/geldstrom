"""Security mechanisms for FinTS PIN/TAN authentication."""
from __future__ import annotations

import datetime
import random
from typing import TYPE_CHECKING, Protocol

from fints.exceptions import FinTSError
from fints.formals import (
    AlgorithmParameterIVName,
    AlgorithmParameterName,
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
from fints.segments.message import HNSHA2, HNSHK4, HNVSD1, HNVSK3
from fints.types import SegmentSequence

if TYPE_CHECKING:
    from fints.message import FinTSMessage


class EncryptionMechanism(Protocol):
    """Protocol for message encryption mechanisms."""

    def encrypt(self, message: "FinTSMessage") -> None:
        """Encrypt the message in place."""
        ...

    def decrypt(self, message: "FinTSMessage") -> None:
        """Decrypt the message in place."""
        ...


class AuthenticationMechanism(Protocol):
    """Protocol for message authentication/signing mechanisms."""

    def sign_prepare(self, message: "FinTSMessage") -> None:
        """Prepare the message for signing (add signature header)."""
        ...

    def sign_commit(self, message: "FinTSMessage") -> None:
        """Complete the signature (add signature trailer)."""
        ...

    def verify(self, message: "FinTSMessage") -> None:
        """Verify the message signature."""
        ...


class PinTanDummyEncryptionMechanism:
    """
    PIN/TAN "encryption" mechanism.

    FinTS PIN/TAN doesn't use real encryption - this wraps messages
    in the required HNVSK/HNVSD envelope structure.
    """

    def __init__(self, security_method_version: int = 1) -> None:
        self.security_method_version = security_method_version

    def encrypt(self, message: "FinTSMessage") -> None:
        """Wrap message in encryption envelope."""
        assert message.segments[0].header.type == "HNHBK"
        assert message.segments[-1].header.type == "HNHBS"

        # Extract plain segments (between header and trailer)
        plain_segments = message.segments[1:-1]
        del message.segments[1:-1]

        _now = datetime.datetime.now()

        # Insert encryption header
        message.segments.insert(
            1,
            HNVSK3(
                security_profile=SecurityProfile(
                    SecurityMethod.PIN, self.security_method_version
                ),
                security_function="998",
                security_role=SecurityRole.ISS,
                security_identification_details=SecurityIdentificationDetails(
                    IdentifiedRole.MS,
                    identifier=message.dialog.client.system_id,
                ),
                security_datetime=SecurityDateTime(
                    DateTimeType.STS,
                    _now.date(),
                    _now.time(),
                ),
                encryption_algorithm=EncryptionAlgorithm(
                    UsageEncryption.OSY,
                    OperationMode.CBC,
                    EncryptionAlgorithmCoded.TWOKEY3DES,
                    b"\x00" * 8,
                    AlgorithmParameterName.KYE,
                    AlgorithmParameterIVName.IVC,
                ),
                key_name=KeyName(
                    message.dialog.client.bank_identifier,
                    message.dialog.client.user_id,
                    KeyType.V,
                    0,
                    0,
                ),
                compression_function=CompressionFunction.NULL,
            ),
        )
        message.segments[1].header.number = 998

        # Insert encrypted data container
        message.segments.insert(
            2,
            HNVSD1(data=SegmentSequence(segments=plain_segments)),
        )
        message.segments[2].header.number = 999

    def decrypt(self, message: "FinTSMessage") -> None:
        """No-op for PIN/TAN - messages are not actually encrypted."""
        pass


class PinTanAuthenticationMechanism:
    """
    Base PIN/TAN authentication mechanism.

    Handles message signing with PIN and optional TAN.
    """

    def __init__(self, pin) -> None:
        self.pin = pin
        self.pending_signature = None
        self.security_function: str | None = None

    def sign_prepare(self, message: "FinTSMessage") -> None:
        """Add signature header to message."""
        _now = datetime.datetime.now()
        rand = random.SystemRandom()

        self.pending_signature = HNSHK4(
            security_profile=SecurityProfile(SecurityMethod.PIN, 1),
            security_function=self.security_function,
            security_reference=rand.randint(1000000, 9999999),
            security_application_area=SecurityApplicationArea.SHM,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                IdentifiedRole.MS,
                identifier=message.dialog.client.system_id,
            ),
            security_reference_number=1,
            security_datetime=SecurityDateTime(
                DateTimeType.STS,
                _now.date(),
                _now.time(),
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
                message.dialog.client.bank_identifier,
                message.dialog.client.user_id,
                KeyType.S,
                0,
                0,
            ),
        )

        message += self.pending_signature

    def _get_tan(self) -> str | None:
        """Get TAN for signature. Override in subclasses."""
        return None

    def sign_commit(self, message: "FinTSMessage") -> None:
        """Complete signature with PIN and optional TAN."""
        if not self.pending_signature:
            raise FinTSError("No signature is pending")

        if self.pending_signature not in message.segments:
            raise FinTSError("Cannot sign a message that was not prepared")

        signature = HNSHA2(
            security_reference=self.pending_signature.security_reference,
            user_defined_signature=UserDefinedSignature(
                pin=self.pin,
                tan=self._get_tan(),
            ),
        )

        self.pending_signature = None
        message += signature

    def verify(self, message: "FinTSMessage") -> None:
        """No-op - response verification not implemented."""
        pass


class PinTanOneStepAuthenticationMechanism(PinTanAuthenticationMechanism):
    """One-step PIN/TAN authentication (no TAN required)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.security_function = "999"


class PinTanTwoStepAuthenticationMechanism(PinTanAuthenticationMechanism):
    """
    Two-step PIN/TAN authentication.

    Uses the specified security function and retrieves TAN from
    the client's TAN workflow when needed.
    """

    def __init__(self, client, security_function: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.client = client
        self.security_function = security_function

    def _get_tan(self) -> str | None:
        """Get pending TAN from client's TAN workflow."""
        return self.client._tan_helper().consume_pending_tan()


__all__ = [
    "AuthenticationMechanism",
    "EncryptionMechanism",
    "PinTanAuthenticationMechanism",
    "PinTanDummyEncryptionMechanism",
    "PinTanOneStepAuthenticationMechanism",
    "PinTanTwoStepAuthenticationMechanism",
]

