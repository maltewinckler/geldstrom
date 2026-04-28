"""FinTS-specific exceptions."""


class FinTSError(Exception):
    """Base exception for all FinTS errors."""


class FinTSClientError(FinTSError):
    """Base exception for FinTS client errors."""


class FinTSClientPINError(FinTSClientError):
    """Raised when the PIN is rejected by the bank."""


class FinTSClientTemporaryAuthError(FinTSClientError):
    """Raised when the bank rejects the request temporarily (e.g. too many attempts)."""


class FinTSSCARequiredError(FinTSClientError):
    """Raised when strong customer authentication (SCA) is required."""


class FinTSDialogError(FinTSError):
    """Base exception for FinTS dialog errors."""


class FinTSDialogStateError(FinTSDialogError):
    """Raised when a dialog operation is attempted in an invalid state."""


class FinTSDialogInitError(FinTSDialogError):
    """Raised when a FinTS dialog cannot be established with the bank."""


class FinTSConnectionError(FinTSError):
    """Raised when a connection error occurs."""


class FinTSUnsupportedOperation(FinTSError):
    """Raised when an unsupported operation is requested."""


class FinTSNoResponseError(FinTSError):
    """Raised when no response is received from the server."""


__all__ = [
    "FinTSError",
    "FinTSClientError",
    "FinTSClientPINError",
    "FinTSClientTemporaryAuthError",
    "FinTSSCARequiredError",
    "FinTSDialogError",
    "FinTSDialogStateError",
    "FinTSDialogInitError",
    "FinTSConnectionError",
    "FinTSUnsupportedOperation",
    "FinTSNoResponseError",
]
