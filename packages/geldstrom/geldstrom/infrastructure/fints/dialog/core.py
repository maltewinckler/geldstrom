"""Dialog class — active FinTS dialog session with TAN strategy dispatch."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from geldstrom.infrastructure.fints.challenge import DecoupledTANPending
from geldstrom.infrastructure.fints.exceptions import (
    FinTSDialogError,
    FinTSDialogInitError,
    FinTSDialogStateError,
)
from geldstrom.infrastructure.fints.protocol import (
    CUSTOMER_ID_ANONYMOUS,
    HKEND1,
    HKIDN2,
    HKVVB3,
    HNHBK3,
    BankIdentifier,
    Language2,
    SystemIDStatus,
)

from .connection import HTTPSDialogConnection
from .responses import ProcessedResponse, ResponseProcessor
from .tan_strategies.base import TANStrategy
from .tan_strategies.decoupled import DecoupledTanStrategy, build_status_hktan
from .tan_strategies.no_tan import NoTanStrategy

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.challenge import ChallengeHandler
    from geldstrom.infrastructure.fints.dialog.message import FinTSCustomerMessage
    from geldstrom.infrastructure.fints.protocol import ParameterStore

    from .security import (
        StandaloneAuthenticationMechanism,
        StandaloneEncryptionMechanism,
    )

# FinTS protocol markers for uninitialized state
DIALOG_ID_UNASSIGNED = "0"
SYSTEM_ID_UNASSIGNED = "0"

logger = logging.getLogger(__name__)


class DialogSnapshot(BaseModel, frozen=True):
    """Serializable snapshot of a Dialog's state for later resumption.

    Captures everything needed to reconstruct a Dialog that can execute
    ``poll_decoupled_once()`` without going through the full initialization
    handshake.
    """

    dialog_id: str
    message_number: int
    country_identifier: str
    bank_code: str
    user_id: str
    customer_id: str
    system_id: str
    product_name: str
    product_version: str
    security_function: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DialogSnapshot:
        return cls.model_validate(data)


class DialogConfig(BaseModel):
    """Configuration for dialog creation."""

    bank_identifier: BankIdentifier
    user_id: str
    customer_id: str
    system_id: str = SYSTEM_ID_UNASSIGNED
    product_name: str = ""
    product_version: str = ""
    language: Language2 = Language2.DE

    model_config = {"arbitrary_types_allowed": True}


class DialogState(BaseModel):
    """Current state of a FinTS dialog."""

    dialog_id: str = DIALOG_ID_UNASSIGNED
    message_number: int = 1
    is_open: bool = False
    is_initialized: bool = False


class Dialog:
    """Active FinTS dialog session with TAN strategy dispatch.

    The Dialog delegates TAN-related behaviour to an injected TANStrategy:
    - NoTanStrategy: pass-through (security_function=999)
    - DecoupledTanStrategy: app-based approval (code 3955)
    """

    def __init__(
        self,
        connection: HTTPSDialogConnection,
        config: DialogConfig,
        parameters: ParameterStore,
        enc_mechanism: StandaloneEncryptionMechanism | None = None,
        auth_mechanisms: Sequence[StandaloneAuthenticationMechanism] | None = None,
        response_processor: ResponseProcessor | None = None,
        tan_strategy: TANStrategy | None = None,
    ) -> None:
        self._connection = connection
        self._config = config
        self._parameters = parameters
        self._enc_mechanism = enc_mechanism
        self._auth_mechanisms = list(auth_mechanisms or [])
        self._response_processor = response_processor or ResponseProcessor()
        self._state = DialogState()
        self._challenge_handler: ChallengeHandler | None = None
        self._tan_strategy = (
            tan_strategy if tan_strategy is not None else NoTanStrategy()
        )

    # ------------------------------------------------------------------
    # Snapshot / Resume
    # ------------------------------------------------------------------

    def snapshot(self) -> DialogSnapshot:
        """Capture a serializable snapshot of this dialog's state.

        Intended to be called while the dialog is open and waiting for
        decoupled TAN approval.  The snapshot can later be used with
        ``Dialog.resume()`` to reconstruct a dialog capable of calling
        ``poll_decoupled_once()``.
        """
        config = self._config
        return DialogSnapshot(
            dialog_id=self._state.dialog_id,
            message_number=self._state.message_number,
            country_identifier=config.bank_identifier.country_identifier,
            bank_code=config.bank_identifier.bank_code or "",
            user_id=config.user_id,
            customer_id=config.customer_id,
            system_id=config.system_id,
            product_name=config.product_name,
            product_version=config.product_version,
            security_function=self._tan_strategy.security_function,
        )

    @classmethod
    def resume(
        cls,
        snapshot: DialogSnapshot,
        connection: HTTPSDialogConnection,
        parameters: ParameterStore,
        enc_mechanism: StandaloneEncryptionMechanism | None = None,
        auth_mechanisms: Sequence[StandaloneAuthenticationMechanism] | None = None,
    ) -> Dialog:
        """Reconstruct a Dialog from a snapshot for decoupled TAN polling.

        The returned dialog has its state pre-populated (``is_open=True``,
        correct ``dialog_id`` and ``message_number``) and is ready for
        ``poll_decoupled_once()`` calls.  It must **not** be used for
        ``initialize()`` or general ``send()`` calls.
        """
        bank_id = BankIdentifier(
            country_identifier=snapshot.country_identifier,
            bank_code=snapshot.bank_code or None,
        )
        config = DialogConfig(
            bank_identifier=bank_id,
            user_id=snapshot.user_id,
            customer_id=snapshot.customer_id,
            system_id=snapshot.system_id,
            product_name=snapshot.product_name,
            product_version=snapshot.product_version,
        )
        tan_strategy = DecoupledTanStrategy(snapshot.security_function)

        dialog = cls(
            connection=connection,
            config=config,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=auth_mechanisms,
            tan_strategy=tan_strategy,
        )
        dialog._state = DialogState(
            dialog_id=snapshot.dialog_id,
            message_number=snapshot.message_number,
            is_open=True,
            is_initialized=True,
        )
        return dialog

    @property
    def tan_strategy(self) -> TANStrategy:
        return self._tan_strategy

    @property
    def is_two_step_tan(self) -> bool:
        return self._tan_strategy.is_two_step

    @property
    def security_function(self) -> str:
        """The active security function code (e.g. '999', '946')."""
        return self._tan_strategy.security_function

    @property
    def dialog_id(self) -> str:
        return self._state.dialog_id

    @property
    def is_open(self) -> bool:
        return self._state.is_open

    @property
    def parameters(self) -> ParameterStore:
        return self._parameters

    def initialize(
        self,
        extra_segments: Sequence = (),
        challenge_handler: ChallengeHandler | None = None,
    ) -> ProcessedResponse:
        if self._state.is_open:
            raise FinTSDialogStateError("Dialog is already open")
        self._challenge_handler = challenge_handler

        segments = self._build_init_segments()
        segments.extend(extra_segments)
        try:
            self._state.is_open = True
            response = self._send_segments(segments, internal=True)
            self._state.is_initialized = True
            if self._state.dialog_id == DIALOG_ID_UNASSIGNED:
                self._state.dialog_id = response.dialog_id

            # Delegate TAN handling to the strategy
            final_response = self._tan_strategy.handle_response(
                response,
                challenge_handler,
                send_tan_callback=self._send_internal,
            )
            if final_response is not None:
                return final_response

            return response

        except DecoupledTANPending:
            # Dialog must stay open — caller will poll externally.
            raise
        except Exception as e:
            self._state.is_open = False
            if isinstance(e, (FinTSDialogError, TimeoutError, ValueError)):
                raise
            raise FinTSDialogInitError("Couldn't establish dialog with bank") from e

    def send(
        self,
        *segments,
        challenge_handler: ChallengeHandler | None = None,
    ) -> ProcessedResponse:
        """Send segments with TAN strategy dispatch.

        Three protocol paths (determined by the active TANStrategy):
        (a) No-TAN: security_function=999, no HKTAN injection, response returned directly.
        (b) Decoupled: bank returns code 3955 → challenge_handler raises
            DecoupledTANPending, detaching the dialog for async TAN approval.
        (c) Interactive TAN: HKTAN injected, challenge presented via challenge_handler
            synchronously, TAN submitted in-dialog.
        """
        effective_handler = challenge_handler or self._challenge_handler
        if not self._state.is_open:
            raise FinTSDialogStateError("Cannot send on dialog that is not open")

        # Step 1: Strategy prepares segments (may inject HKTAN)
        segment_list = self._tan_strategy.prepare_segments(
            list(segments),
            self._parameters,
        )
        # Step 2: Send
        response = self._send_segments(segment_list, internal=False)
        # Step 3: Strategy handles response (TAN processing)
        final_response = self._tan_strategy.handle_response(
            response,
            effective_handler,
            send_tan_callback=self._send_internal,
        )
        return final_response if final_response is not None else response

    def poll_decoupled_once(self, task_reference: str) -> ProcessedResponse | None:
        """Send a single HKTAN status query. Returns response on approval, None if still waiting."""
        status_hktan = build_status_hktan(
            self._parameters.bpd.segments,
            task_reference,
        )
        response = self._send_segments([status_hktan], internal=True)

        if response.get_response_by_code("3956"):
            return None

        if response.has_errors:
            error_resp = next((r for r in response.all_responses if r.is_error), None)
            err_text = error_resp.text if error_resp else "Unknown error"
            logger.error("Decoupled TAN polling failed: %s", err_text)
            if "Nachricht enthält Fehler" in err_text or "message" in err_text.lower():
                raise TimeoutError(
                    "The bank's TAN request expired. Please try again and approve "
                    "the request in your banking app before it times out."
                )
            raise ValueError(f"Decoupled TAN rejected: {err_text}")

        return response

    def end(self) -> None:
        if not self._state.is_open:
            return
        try:
            self._send_segments(
                [HKEND1(dialog_id=self._state.dialog_id)], internal=True
            )
        finally:
            self._state.is_open = False

    # ------------------------------------------------------------------
    # Internal transport
    # ------------------------------------------------------------------

    def _send_internal(self, segments: list) -> ProcessedResponse:
        """Internal send callback for TAN strategies (no TAN re-processing)."""
        return self._send_segments(segments, internal=True)

    def _build_init_segments(self) -> list:
        config = self._config
        params = self._parameters

        system_id_status = (
            SystemIDStatus.ID_UNNECESSARY
            if config.customer_id == CUSTOMER_ID_ANONYMOUS
            else SystemIDStatus.ID_NECESSARY
        )

        return [
            HKIDN2(
                bank_identifier=config.bank_identifier,
                customer_id=config.customer_id,
                system_id=config.system_id,
                system_id_status=system_id_status,
            ),
            HKVVB3(
                bpd_version=params.bpd_version,
                upd_version=params.upd_version,
                language=config.language,
                product_name=config.product_name,
                product_version=config.product_version,
            ),
        ]

    def _send_segments(
        self, segments: Sequence, internal: bool = False
    ) -> ProcessedResponse:
        message = self._build_message(segments)
        raw_response = self._connection.send(message)
        self._state.message_number += 1
        processed = self._response_processor.process(raw_response)
        self._parameters.update_from_response(
            bpa=processed.bpa,
            bpd_version=processed.bpd_version,
            bpd_segments=processed.bpd_segments,
            upa=processed.upa,
            upd_version=processed.upd_version,
            upd_segments=processed.upd_segments,
        )

        if self._state.dialog_id == DIALOG_ID_UNASSIGNED:
            self._state.dialog_id = processed.dialog_id
        return processed

    def _build_message(self, segments: Sequence) -> FinTSCustomerMessage:
        from geldstrom.infrastructure.fints.protocol import HNHBS1

        message = self._create_message_with_header()
        for auth_mech in self._auth_mechanisms:
            auth_mech.sign_prepare(message)
        for seg in segments:
            message += seg
        for auth_mech in reversed(self._auth_mechanisms):
            auth_mech.sign_commit(message)
        message += HNHBS1(message_number=self._state.message_number)
        if self._enc_mechanism:
            self._enc_mechanism.encrypt(message)
        message.segments[0].message_size = len(message.render_bytes())
        return message

    def _create_message_with_header(self) -> FinTSCustomerMessage:
        from geldstrom.infrastructure.fints.dialog.message import FinTSCustomerMessage

        message = FinTSCustomerMessage()
        message += HNHBK3(
            message_size=0,
            hbci_version=300,
            dialog_id=self._state.dialog_id,
            message_number=self._state.message_number,
        )

        return message
