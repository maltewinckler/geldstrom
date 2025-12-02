"""FinTS dialog infrastructure for managing bank connections."""

from .connection import ConnectionConfig, HTTPSDialogConnection
from .factory import (
    DIALOG_ID_UNASSIGNED,
    SYSTEM_ID_UNASSIGNED,
    Dialog,
    DialogConfig,
    DialogFactory,
    DialogState,
)
from .responses import DialogResponse, ProcessedResponse, ResponseProcessor

__all__ = [
    "ConnectionConfig",
    "Dialog",
    "DialogConfig",
    "DialogFactory",
    "DialogResponse",
    "DialogState",
    "DIALOG_ID_UNASSIGNED",
    "HTTPSDialogConnection",
    "ProcessedResponse",
    "ResponseProcessor",
    "SYSTEM_ID_UNASSIGNED",
]
