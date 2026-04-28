"""FinTS-specific exceptions."""


class FinTSError(Exception):
    """Base exception for all FinTS errors."""


class FinTSClientError(FinTSError):
    """Base exception for FinTS client errors."""


class FinTSSCARequiredError(FinTSClientError):
    """Raised when strong customer authentication (SCA) is required."""


class FinTSDialogError(FinTSError):
    """Base exception for FinTS dialog errors."""


class FinTSConnectionError(FinTSError):
    """Raised when a connection error occurs."""


class FinTSUnsupportedOperation(FinTSError):
    """Raised when an unsupported operation is requested."""


class FinTSNoResponseError(FinTSError):
    """Raised when no response is received from the server."""


__all__ = [
    "FinTSError",
    "FinTSClientError",
    "FinTSSCARequiredError",
    "FinTSDialogError",
    "FinTSConnectionError",
    "FinTSUnsupportedOperation",
    "FinTSNoResponseError",
]
