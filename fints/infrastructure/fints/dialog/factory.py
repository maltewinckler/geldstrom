"""Dialog factory for creating and managing FinTS dialogs."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, Sequence

from fints.constants import SYSTEM_ID_UNASSIGNED
from fints.exceptions import FinTSDialogError, FinTSDialogInitError, FinTSDialogStateError
from fints.formals import CUSTOMER_ID_ANONYMOUS, Language2, SystemIDStatus
from fints.segments.auth import HKIDN2, HKVVB3
from fints.segments.dialog import HKEND1
from fints.segments.message import HNHBK3

from .connection import ConnectionConfig, HTTPSDialogConnection
from .responses import ProcessedResponse, ResponseProcessor
from .transport import DIALOG_ID_UNASSIGNED

if TYPE_CHECKING:
    from fints.infrastructure.fints.protocol import ParameterStore
    from fints.security import AuthenticationMechanism, EncryptionMechanism

logger = logging.getLogger(__name__)


@dataclass
class DialogConfig:
    """Configuration for dialog creation."""

    bank_identifier: object
    user_id: str
    customer_id: str
    system_id: str = SYSTEM_ID_UNASSIGNED
    product_name: str = ""
    product_version: str = ""
    language: Language2 = Language2.DE


@dataclass
class DialogState:
    """Current state of a FinTS dialog."""

    dialog_id: str = DIALOG_ID_UNASSIGNED
    message_number: int = 1
    is_open: bool = False
    is_initialized: bool = False


class Dialog:
    """
    Represents an active FinTS dialog session.

    A dialog is a sequence of related message exchanges with the bank.
    It must be initialized before use and properly closed when done.
    """

    def __init__(
        self,
        connection: HTTPSDialogConnection,
        config: DialogConfig,
        parameters: "ParameterStore",
        enc_mechanism: "EncryptionMechanism | None" = None,
        auth_mechanisms: "Sequence[AuthenticationMechanism] | None" = None,
        response_processor: ResponseProcessor | None = None,
    ) -> None:
        """
        Initialize dialog.

        Args:
            connection: HTTP connection to use
            config: Dialog configuration
            parameters: Parameter store for BPD/UPD
            enc_mechanism: Optional encryption mechanism
            auth_mechanisms: Optional authentication mechanisms
            response_processor: Optional custom response processor
        """
        self._connection = connection
        self._config = config
        self._parameters = parameters
        self._enc_mechanism = enc_mechanism
        self._auth_mechanisms = list(auth_mechanisms or [])
        self._response_processor = response_processor or ResponseProcessor()
        self._state = DialogState()

    @property
    def dialog_id(self) -> str:
        """Return current dialog ID."""
        return self._state.dialog_id

    @property
    def is_open(self) -> bool:
        """Return True if dialog is currently open."""
        return self._state.is_open

    @property
    def parameters(self) -> "ParameterStore":
        """Return the parameter store."""
        return self._parameters

    def initialize(self, extra_segments: Sequence = ()) -> ProcessedResponse:
        """
        Initialize the dialog with the bank.

        Args:
            extra_segments: Additional segments to include in init message

        Returns:
            Processed response from the bank

        Raises:
            FinTSDialogStateError: If dialog is already open
            FinTSDialogInitError: If initialization fails
        """
        if self._state.is_open:
            raise FinTSDialogStateError("Dialog is already open")

        # Build initialization segments
        segments = self._build_init_segments()
        segments.extend(extra_segments)

        try:
            self._state.is_open = True
            response = self._send_segments(segments, internal=True)
            self._state.is_initialized = True

            # Extract dialog ID from response
            if self._state.dialog_id == DIALOG_ID_UNASSIGNED:
                self._state.dialog_id = response.dialog_id

            return response

        except Exception as e:
            self._state.is_open = False
            if isinstance(e, (FinTSDialogError,)):
                raise
            raise FinTSDialogInitError(
                "Couldn't establish dialog with bank"
            ) from e

    def send(self, *segments) -> ProcessedResponse:
        """
        Send segments to the bank within this dialog.

        Args:
            *segments: Segments to send

        Returns:
            Processed response from the bank

        Raises:
            FinTSDialogStateError: If dialog is not open
        """
        if not self._state.is_open:
            raise FinTSDialogStateError("Cannot send on dialog that is not open")

        return self._send_segments(list(segments), internal=False)

    def end(self) -> None:
        """
        End the dialog session.

        Sends HKEND to properly close the dialog with the bank.
        """
        if not self._state.is_open:
            return

        try:
            self._send_segments([HKEND1(self._state.dialog_id)], internal=True)
        finally:
            self._state.is_open = False

    def _build_init_segments(self) -> list:
        """Build the segments needed for dialog initialization."""
        config = self._config
        params = self._parameters

        system_id_status = (
            SystemIDStatus.ID_UNNECESSARY
            if config.customer_id == CUSTOMER_ID_ANONYMOUS
            else SystemIDStatus.ID_NECESSARY
        )

        return [
            HKIDN2(
                config.bank_identifier,
                config.customer_id,
                config.system_id,
                system_id_status,
            ),
            HKVVB3(
                params.bpd_version,
                params.upd_version,
                config.language,
                config.product_name,
                config.product_version,
            ),
        ]

    def _send_segments(
        self, segments: Sequence, internal: bool = False
    ) -> ProcessedResponse:
        """
        Send segments and process the response.

        Args:
            segments: Segments to send
            internal: Whether this is an internal message (init/end)

        Returns:
            Processed response
        """
        from fints.message import FinTSCustomerMessage, MessageDirection

        # Build message
        message = self._build_message(segments)

        # Send via connection
        raw_response = self._connection.send(message)

        # Track message number
        self._state.message_number += 1

        # Process response
        processed = self._response_processor.process(raw_response)

        # Update parameters if present
        self._parameters.update_from_response(
            bpa=processed.bpa,
            bpd_version=processed.bpd_version,
            bpd_segments=processed.bpd_segments,
            upa=processed.upa,
            upd_version=processed.upd_version,
            upd_segments=processed.upd_segments,
        )

        # Update dialog ID if needed
        if self._state.dialog_id == DIALOG_ID_UNASSIGNED:
            self._state.dialog_id = processed.dialog_id

        return processed

    def _build_message(self, segments: Sequence) -> "FinTSCustomerMessage":
        """Build a FinTS message from segments."""
        from fints.message import FinTSCustomerMessage
        from fints.segments.message import HNHBS1

        # Create message with header
        message = self._create_message_with_header()

        # Prepare signatures
        for auth_mech in self._auth_mechanisms:
            auth_mech.sign_prepare(message)

        # Add body segments
        for seg in segments:
            message += seg

        # Commit signatures (reverse order)
        for auth_mech in reversed(self._auth_mechanisms):
            auth_mech.sign_commit(message)

        # Add trailer
        message += HNHBS1(self._state.message_number)

        # Apply encryption
        if self._enc_mechanism:
            self._enc_mechanism.encrypt(message)

        # Update message size
        message.segments[0].message_size = len(message.render_bytes())

        return message

    def _create_message_with_header(self) -> "FinTSCustomerMessage":
        """Create a new message with header initialized."""
        from fints.message import FinTSCustomerMessage

        # Create minimal dialog context for message
        class MinimalContext:
            def __init__(ctx_self):
                ctx_self.bank_identifier = self._config.bank_identifier
                ctx_self.user_id = self._config.user_id
                ctx_self.system_id = self._config.system_id

            @property
            def client(ctx_self):
                return ctx_self

        message = FinTSCustomerMessage.__new__(FinTSCustomerMessage)
        message.dialog = MinimalContext()
        message.segments = []

        # Add header
        message += HNHBK3(
            0, 300, self._state.dialog_id, self._state.message_number
        )

        return message


class DialogFactory:
    """
    Factory for creating and managing FinTS dialogs.

    This class provides a clean interface for:
    - Creating new dialogs with proper configuration
    - Managing dialog lifecycle (open/close)
    - Reusing connections across dialogs
    """

    def __init__(
        self,
        connection_config: ConnectionConfig | str,
        dialog_config: DialogConfig,
        parameters: "ParameterStore",
        enc_mechanism_factory=None,
        auth_mechanism_factory=None,
    ) -> None:
        """
        Initialize dialog factory.

        Args:
            connection_config: Connection configuration or URL
            dialog_config: Dialog configuration
            parameters: Parameter store for BPD/UPD
            enc_mechanism_factory: Optional callable to create encryption mechanism
            auth_mechanism_factory: Optional callable to create auth mechanisms
        """
        if isinstance(connection_config, str):
            connection_config = ConnectionConfig(url=connection_config)
        self._connection_config = connection_config
        self._dialog_config = dialog_config
        self._parameters = parameters
        self._enc_factory = enc_mechanism_factory
        self._auth_factory = auth_mechanism_factory

    @contextmanager
    def open_dialog(
        self,
        lazy_init: bool = False,
        extra_init_segments: Sequence = (),
    ) -> Iterator[Dialog]:
        """
        Open a dialog as a context manager.

        Args:
            lazy_init: If True, defer initialization until first send
            extra_init_segments: Additional segments for init message

        Yields:
            Initialized dialog

        Example:
            with factory.open_dialog() as dialog:
                response = dialog.send(segment)
        """
        connection = HTTPSDialogConnection(self._connection_config)

        # Create mechanisms
        enc_mech = self._enc_factory() if self._enc_factory else None
        auth_mechs = self._auth_factory() if self._auth_factory else []

        dialog = Dialog(
            connection=connection,
            config=self._dialog_config,
            parameters=self._parameters,
            enc_mechanism=enc_mech,
            auth_mechanisms=auth_mechs,
        )

        try:
            if not lazy_init:
                dialog.initialize(extra_init_segments)
            yield dialog
        finally:
            if dialog.is_open:
                try:
                    dialog.end()
                except Exception:
                    logger.exception("Error closing dialog")
            connection.close()

    def create_dialog(self) -> Dialog:
        """
        Create a dialog without opening it.

        Use this when you need more control over the dialog lifecycle.

        Returns:
            Uninitialized dialog instance
        """
        connection = HTTPSDialogConnection(self._connection_config)

        enc_mech = self._enc_factory() if self._enc_factory else None
        auth_mechs = self._auth_factory() if self._auth_factory else []

        return Dialog(
            connection=connection,
            config=self._dialog_config,
            parameters=self._parameters,
            enc_mechanism=enc_mech,
            auth_mechanisms=auth_mechs,
        )

