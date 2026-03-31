"""FinTS-specific exceptions."""


class FinTSError(Exception):
    """Base exception for all FinTS errors."""

    pass


class FinTSClientError(FinTSError):
    """Client-side error."""

    pass


class FinTSClientPINError(FinTSClientError):
    """PIN-related error."""

    pass


class FinTSClientTemporaryAuthError(FinTSClientError):
    """Temporary authentication error."""

    pass


class FinTSSCARequiredError(FinTSClientError):
    """Strong Customer Authentication required."""

    pass


class FinTSDialogError(FinTSError):
    """Dialog-related error."""

    pass


class FinTSDialogStateError(FinTSDialogError):
    """Invalid dialog state error."""

    pass


class FinTSDialogOfflineError(FinTSDialogError):
    """Dialog offline error."""

    pass


class FinTSDialogInitError(FinTSDialogError):
    """Dialog initialization error."""

    pass


class FinTSConnectionError(FinTSError):
    """Connection error."""

    pass


class FinTSUnsupportedOperation(FinTSError):
    """Operation not supported by bank."""

    pass


class FinTSNoResponseError(FinTSError):
    """No response received from bank."""

    pass


__all__ = [
    "FinTSClientError",
    "FinTSClientPINError",
    "FinTSClientTemporaryAuthError",
    "FinTSConnectionError",
    "FinTSDialogError",
    "FinTSDialogInitError",
    "FinTSDialogOfflineError",
    "FinTSDialogStateError",
    "FinTSError",
    "FinTSNoResponseError",
    "FinTSSCARequiredError",
    "FinTSUnsupportedOperation",
]
