"""FinTS protocol engine - session management, transport, and security.

This package handles the low-level FinTS dialog lifecycle:
- Opening/closing FinTS dialog sessions (``core``)
- HTTP(S) transport and message framing (``connection``, ``message``)
- Message signing and encryption envelopes (``security``)
- TAN strategy dispatch for authentication (``tan_strategies``)
- Response parsing and BPD/UPD extraction (``responses``)

Consumers should not use this package directly for business logic;
use ``operations`` for segment-level requests and ``services`` for
end-to-end orchestration with domain mapping.
"""

from .challenge import FinTSChallenge
from .connection import ConnectionConfig, HTTPSDialogConnection
from .core import (
    DIALOG_ID_UNASSIGNED,
    SYSTEM_ID_UNASSIGNED,
    Dialog,
    DialogConfig,
    DialogSnapshot,
    DialogState,
)
from .logging import LogConfiguration, Password, log_configuration
from .message import (
    FinTSCustomerMessage,
    FinTSInstituteMessage,
    FinTSMessage,
    MessageDirection,
)
from .responses import DialogResponse, ProcessedResponse, ResponseProcessor
from .security import (
    SecurityContext,
    StandaloneAuthenticationMechanism,
    StandaloneEncryptionMechanism,
)
from .tan_strategies import (
    DecoupledTanStrategy,
    NoTanStrategy,
    TANStrategy,
)

__all__ = [
    "ConnectionConfig",
    "DecoupledTanStrategy",
    "Dialog",
    "DialogConfig",
    "DialogResponse",
    "DialogSnapshot",
    "DialogState",
    "DIALOG_ID_UNASSIGNED",
    "FinTSChallenge",
    "FinTSCustomerMessage",
    "FinTSInstituteMessage",
    "FinTSMessage",
    "HTTPSDialogConnection",
    "LogConfiguration",
    "MessageDirection",
    "NoTanStrategy",
    "Password",
    "ProcessedResponse",
    "ResponseProcessor",
    "SecurityContext",
    "StandaloneAuthenticationMechanism",
    "StandaloneEncryptionMechanism",
    "SYSTEM_ID_UNASSIGNED",
    "TANStrategy",
    "log_configuration",
]
