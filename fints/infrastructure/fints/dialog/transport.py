"""Message transport handling for FinTS dialogs."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, Sequence

from fints.message import FinTSCustomerMessage, FinTSInstituteMessage, MessageDirection
from fints.segments.message import HNHBK3, HNHBS1

if TYPE_CHECKING:
    from fints.security import AuthenticationMechanism, EncryptionMechanism
    from .connection import DialogConnection

logger = logging.getLogger(__name__)

DIALOG_ID_UNASSIGNED = "0"


class MessageTransport(Protocol):
    """Protocol for sending and receiving FinTS messages."""

    def send_message(
        self,
        segments: Sequence,
        dialog_id: str,
        message_number: int,
    ) -> FinTSInstituteMessage:
        """
        Send message segments and receive the response.

        Args:
            segments: Segments to include in the message
            dialog_id: Current dialog identifier
            message_number: Sequence number for this message

        Returns:
            Institute response message
        """
        ...


class FinTSMessageTransport:
    """
    Handles message construction, encryption, signing, and transmission.

    This class manages the low-level details of:
    - Constructing FinTS messages from segments
    - Applying encryption mechanisms
    - Applying authentication/signature mechanisms
    - Sending messages via the connection
    - Tracking message numbers
    """

    def __init__(
        self,
        connection: "DialogConnection",
        bank_identifier,
        user_id: str,
        system_id: str,
        enc_mechanism: "EncryptionMechanism | None" = None,
        auth_mechanisms: "Sequence[AuthenticationMechanism] | None" = None,
    ) -> None:
        """
        Initialize message transport.

        Args:
            connection: Connection to use for sending/receiving
            bank_identifier: Bank identifier for messages
            user_id: User identifier for signatures
            system_id: System identifier for signatures
            enc_mechanism: Optional encryption mechanism
            auth_mechanisms: Optional list of authentication mechanisms
        """
        self._connection = connection
        self._bank_identifier = bank_identifier
        self._user_id = user_id
        self._system_id = system_id
        self._enc_mechanism = enc_mechanism
        self._auth_mechanisms = list(auth_mechanisms or [])

        # Message tracking
        self._message_numbers: dict[MessageDirection, int] = {
            v: 1 for v in MessageDirection
        }
        self._messages: dict[MessageDirection, dict[int, object]] = {
            v: {} for v in MessageDirection
        }

    @property
    def next_outgoing_number(self) -> int:
        """Return the next outgoing message number."""
        return self._message_numbers[MessageDirection.TO_CUSTOMER]

    def send_segments(
        self,
        segments: Sequence,
        dialog_id: str,
    ) -> FinTSInstituteMessage:
        """
        Build and send a message from segments.

        Args:
            segments: Segments to include in the message body
            dialog_id: Current dialog identifier

        Returns:
            Institute response message
        """
        direction = MessageDirection.TO_CUSTOMER
        msg_num = self._message_numbers[direction]

        # Build message
        message = self._build_message(segments, dialog_id, msg_num)

        # Track outgoing message
        self._messages[direction][msg_num] = message
        self._message_numbers[direction] += 1

        # Send and receive
        response = self._connection.send(message)

        # Track incoming response
        resp_direction = response.DIRECTION
        resp_num = response.segments[0].message_number
        self._messages[resp_direction][resp_num] = response
        self._message_numbers[resp_direction] = resp_num + 1

        # Decrypt if needed
        if self._enc_mechanism:
            self._enc_mechanism.decrypt(message)

        # Verify signatures
        for auth_mech in self._auth_mechanisms:
            auth_mech.verify(message)

        return response

    def _build_message(
        self,
        segments: Sequence,
        dialog_id: str,
        message_number: int,
    ) -> FinTSCustomerMessage:
        """
        Build a complete FinTS message from segments.

        Args:
            segments: Body segments for the message
            dialog_id: Current dialog identifier
            message_number: Sequence number for this message

        Returns:
            Constructed customer message ready to send
        """
        # Create message wrapper (requires dialog reference for legacy compatibility)
        # We create a minimal dialog-like object for the message
        message = _create_customer_message(
            dialog_id=dialog_id,
            message_number=message_number,
            bank_identifier=self._bank_identifier,
            user_id=self._user_id,
            system_id=self._system_id,
        )

        # Prepare signatures
        for auth_mech in self._auth_mechanisms:
            auth_mech.sign_prepare(message)

        # Add body segments
        for seg in segments:
            message += seg

        # Commit signatures (in reverse order: inner to outer)
        for auth_mech in reversed(self._auth_mechanisms):
            auth_mech.sign_commit(message)

        # Add message trailer
        message += HNHBS1(message_number)

        # Apply encryption
        if self._enc_mechanism:
            self._enc_mechanism.encrypt(message)

        # Update message size in header
        message.segments[0].message_size = len(message.render_bytes())

        return message


class _MinimalDialogContext:
    """
    Minimal dialog context for message construction.

    This provides the minimum interface needed by FinTSCustomerMessage
    and security mechanisms without requiring a full dialog instance.
    """

    def __init__(
        self,
        bank_identifier,
        user_id: str,
        system_id: str,
    ) -> None:
        self.bank_identifier = bank_identifier
        self.user_id = user_id
        self.system_id = system_id

    @property
    def client(self):
        """Return self as a minimal client-like interface."""
        return self


def _create_customer_message(
    dialog_id: str,
    message_number: int,
    bank_identifier,
    user_id: str,
    system_id: str,
) -> FinTSCustomerMessage:
    """
    Create a customer message with header initialized.

    This creates a message that can be used for segment addition
    and encryption without requiring a full dialog context.
    """
    # Create minimal dialog context
    context = _MinimalDialogContext(bank_identifier, user_id, system_id)

    # FinTSCustomerMessage needs a dialog with certain attributes
    # We'll patch the message after creation
    message = FinTSCustomerMessage.__new__(FinTSCustomerMessage)
    message.dialog = context
    message.segments = []

    # Add message header
    message += HNHBK3(0, 300, dialog_id, message_number)

    return message

