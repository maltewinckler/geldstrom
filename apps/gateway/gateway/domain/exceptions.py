"""Gateway domain-layer exceptions.

Each exception carries contextual attributes so that upstream layers
(API error handlers, logging) can produce informative responses without
coupling to the domain internals.
"""

from __future__ import annotations


class GatewayDomainError(Exception):
    """Base for all domain-layer errors."""


class SessionNotFoundError(GatewayDomainError):
    """Raised when a PendingChallenge cannot be found for a SessionIdentity."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"No pending challenge found for session '{session_id}'")


class UnsupportedProtocolError(GatewayDomainError):
    """Raised when a BankingProtocol has no registered handler."""

    def __init__(self, protocol: str) -> None:
        self.protocol = protocol
        super().__init__(f"No handler registered for protocol '{protocol}'")


class BankNotSupportedError(GatewayDomainError):
    """Raised when a bank_code cannot be resolved for the given protocol."""

    def __init__(self, bank_code: str, protocol: str) -> None:
        self.bank_code = bank_code
        self.protocol = protocol
        super().__init__(
            f"Bank '{bank_code}' is not supported for protocol '{protocol}'"
        )


class BankConnectionError(GatewayDomainError):
    """Raised when the banking client cannot connect to the bank."""

    def __init__(self, bank_code: str, reason: str | None = None) -> None:
        self.bank_code = bank_code
        self.reason = reason
        msg = f"Failed to connect to bank '{bank_code}'"
        if reason:
            msg = f"{msg}: {reason}"
        super().__init__(msg)


class TANRejectedError(GatewayDomainError):
    """Raised when the bank rejects the provided TAN response."""

    def __init__(self, session_id: str, reason: str | None = None) -> None:
        self.session_id = session_id
        self.reason = reason
        msg = f"TAN rejected for session '{session_id}'"
        if reason:
            msg = f"{msg}: {reason}"
        super().__init__(msg)
