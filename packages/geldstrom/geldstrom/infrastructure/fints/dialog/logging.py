"""Logging utilities for FinTS dialog communication."""

import re
import threading
from contextlib import contextmanager

# Patterns for credential masking in log output
# These patterns match common formats where PIN/TAN appear in serialized messages
_CREDENTIAL_PATTERNS = [
    # UserDefinedSignature in repr: pin='value' or pin="value"
    (re.compile(r"pin=['\"]([^'\"]+)['\"]", re.IGNORECASE), r"pin='***'"),
    # TAN in repr: tan='value' or tan="value"
    (re.compile(r"tan=['\"]([^'\"]+)['\"]", re.IGNORECASE), r"tan='***'"),
    # Wire format: PIN appears after + separator in HNSHA segment
    # e.g., HNSHA:...:...+reference+pin' or +pin:tan'
    (re.compile(r"(\+[^+:']*\+)([^+:']+)('|\+|:)"), r"\1***\3"),
]


def mask_credentials(text: str) -> str:
    """Mask sensitive credentials from log output.

    Replaces PIN and TAN values with '***' to prevent credential leakage.
    """
    result = text
    for pattern, replacement in _CREDENTIAL_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class Password(str):
    """Password wrapper that can be protected from logging.

    When protected, str() returns '***' instead of the actual value.
    """

    protected = False

    def __init__(self, value):
        self.value = value
        self.blocked = False

    @classmethod
    @contextmanager
    def protect(cls):
        """Context manager to protect passwords from logging."""
        try:
            cls.protected = True
            yield None
        finally:
            cls.protected = False

    def block(self):
        """Block further use of this password."""
        self.blocked = True

    def __str__(self):
        if self.blocked and not self.protected:
            raise RuntimeError("Refusing to use PIN after block")
        return "***" if self.protected else str(self.value)

    def __repr__(self):
        return self.__str__().__repr__()

    def __add__(self, other):
        return self.__str__().__add__(other)

    def replace(self, *args, **kwargs):
        return self.__str__().replace(*args, **kwargs)


class LogConfiguration(threading.local):
    """Thread-local configuration object to guide log output.

    Attributes:
        reduced: Reduce verbosity by suppressing encryption/signature elements
    """

    def __init__(self, reduced: bool = False):
        super().__init__()
        self.reduced = reduced

    @staticmethod
    def set(reduced: bool = False):
        """Permanently change the log configuration for this thread."""
        log_configuration.reduced = reduced

    @staticmethod
    @contextmanager
    def changed(reduced: bool = False):
        """Temporarily change the log configuration for this thread."""
        old_reduced = log_configuration.reduced
        log_configuration.set(reduced=reduced)
        yield
        log_configuration.set(reduced=old_reduced)


# Global thread-local log configuration
log_configuration = LogConfiguration()


__all__ = ["LogConfiguration", "Password", "log_configuration", "mask_credentials"]
