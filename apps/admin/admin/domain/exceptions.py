"""Domain exceptions for the Admin service."""


class AccountNotFoundError(Exception):
    """Raised when an account is not found."""

    pass


class AccountHasKeysError(Exception):
    """Raised when attempting to delete an account that has API keys."""

    pass


class ApiKeyNotFoundError(Exception):
    """Raised when an API key is not found."""

    pass


class ApiKeyAlreadyExistsError(Exception):
    """Raised when attempting to create an API key that already exists for an account."""

    pass


class ApiKeyAlreadyRevokedError(Exception):
    """Raised when attempting to revoke an already revoked API key."""

    pass


class BankEndpointNotFoundError(Exception):
    """Raised when a bank endpoint is not found."""

    pass


class BankEndpointAlreadyExistsError(Exception):
    """Raised when attempting to create a bank endpoint that already exists."""

    pass
