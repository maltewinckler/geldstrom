"""Dialog factory for creating and managing FinTS dialogs."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from geldstrom.domain.connection import ChallengeHandler
from geldstrom.infrastructure.fints.dialog.challenge import FinTSChallenge
from geldstrom.infrastructure.fints.exceptions import (
    FinTSDialogError,
    FinTSDialogInitError,
    FinTSDialogStateError,
)
from geldstrom.infrastructure.fints.protocol import (
    CUSTOMER_ID_ANONYMOUS,
    HKEND1,
    HKIDN2,
    HKTAN_VERSIONS,
    HKVVB3,
    HNHBK3,
    Language2,
    SystemIDStatus,
)

from .connection import ConnectionConfig, HTTPSDialogConnection
from .responses import ProcessedResponse, ResponseProcessor

# FinTS protocol markers for uninitialized state
DIALOG_ID_UNASSIGNED = "0"
SYSTEM_ID_UNASSIGNED = "0"

# Segments that should NOT have HKTAN added (dialog management segments only)
# IMPORTANT: Business segments like HKSPA and HKSAL *may* require HKTAN
# depending on the bank. DKB requires TAN for all operations, Triodos doesn't.
# The safest approach is to always inject HKTAN for business segments.
DIALOG_SEGMENTS = {"HKIDN", "HKVVB", "HKEND", "HKSYN", "HKTAN"}


def _find_highest_hitans(bpd_segments) -> Any | None:
    """Find the highest version HITANS segment in BPD."""
    hitans = None
    for seg in bpd_segments.find_segments("HITANS"):
        if hitans is None or seg.header.version > hitans.header.version:
            hitans = seg
    return hitans


def _get_hktan_class(hitans_version: int) -> tuple[type | None, int]:
    hktan_class = HKTAN_VERSIONS.get(hitans_version)
    if hktan_class:
        return hktan_class, hitans_version
    for v in sorted(HKTAN_VERSIONS.keys(), reverse=True):
        if v <= hitans_version:
            return HKTAN_VERSIONS[v], v
    return None, 0


if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog.message import FinTSCustomerMessage
    from geldstrom.infrastructure.fints.protocol import ParameterStore

    from .security import (
        StandaloneAuthenticationMechanism,
        StandaloneEncryptionMechanism,
    )

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
    """Active FinTS dialog session; handles two-step TAN injection and decoupled polling."""

    def __init__(
        self,
        connection: HTTPSDialogConnection,
        config: DialogConfig,
        parameters: ParameterStore,
        enc_mechanism: StandaloneEncryptionMechanism | None = None,
        auth_mechanisms: Sequence[StandaloneAuthenticationMechanism] | None = None,
        response_processor: ResponseProcessor | None = None,
        security_function: str = "999",
    ) -> None:
        self._connection = connection
        self._config = config
        self._parameters = parameters
        self._enc_mechanism = enc_mechanism
        self._auth_mechanisms = list(auth_mechanisms or [])
        self._response_processor = response_processor or ResponseProcessor()
        self._state = DialogState()
        self._security_function = security_function

    @property
    def is_two_step_tan(self) -> bool:
        return self._security_function != "999"

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
        decoupled_timeout: float = 120.0,
        decoupled_poll_interval: float = 2.0,
        challenge_handler: ChallengeHandler | None = None,
    ) -> ProcessedResponse:
        if self._state.is_open:
            raise FinTSDialogStateError("Dialog is already open")

        segments = self._build_init_segments()
        segments.extend(extra_segments)
        try:
            self._state.is_open = True
            response = self._send_segments(segments, internal=True)
            self._state.is_initialized = True
            if self._state.dialog_id == DIALOG_ID_UNASSIGNED:
                self._state.dialog_id = response.dialog_id
                # Code 3955 = app approval required for dialog init (e.g. DKB).
                logger.info(
                    "Decoupled TAN required for dialog initialization - "
                    "waiting for app approval..."
                )
                final_response = self._handle_decoupled_tan(
                    response,
                    decoupled_timeout,
                    decoupled_poll_interval,
                    challenge_handler,
                )
                if final_response is not None:
                    return final_response

            return response

        except Exception as e:
            self._state.is_open = False
            if isinstance(e, (FinTSDialogError, TimeoutError, ValueError)):
                raise
            raise FinTSDialogInitError("Couldn't establish dialog with bank") from e

    def send(
        self,
        *segments,
        decoupled_timeout: float = 120.0,
        decoupled_poll_interval: float = 2.0,
        challenge_handler: ChallengeHandler | None = None,
    ) -> ProcessedResponse:
        """Send segments; injects HKTAN for business ops and handles decoupled polling."""
        if not self._state.is_open:
            raise FinTSDialogStateError("Cannot send on dialog that is not open")

        segment_list = list(segments)
        if self.is_two_step_tan:
            segment_list = self._inject_hktan_for_business_segments(segment_list)
        response = self._send_segments(segment_list, internal=False)
        # Code 3955 = app approval required.
        if response.get_response_by_code("3955"):
            logger.info(
                "Decoupled TAN required for operation - waiting for app approval..."
            )
            final_response = self._handle_decoupled_tan(
                response,
                decoupled_timeout,
                decoupled_poll_interval,
                challenge_handler,
            )
            if final_response is not None:
                return final_response

        return response

    def _inject_hktan_for_business_segments(self, segments: list) -> list:
        """Inject HKTAN after business segments when HIPINS requires TAN."""
        result = []
        for seg in segments:
            result.append(seg)

            seg_type = (
                getattr(seg.header, "type", None) if hasattr(seg, "header") else None
            )
            if seg_type and seg_type not in DIALOG_SEGMENTS:
                if self._segment_requires_tan(seg_type):
                    hktan = self._build_hktan_for_segment(seg_type)
                    if hktan:
                        logger.debug("Injecting HKTAN for %s operation", seg_type)
                        result.append(hktan)

        return result

    def _segment_requires_tan(self, segment_type: str) -> bool:
        """Check HIPINS in BPD to determine if this segment requires TAN."""
        from geldstrom.infrastructure.fints.protocol import HIPINS1

        hipins = self._parameters.bpd.segments.find_segment_first(HIPINS1)
        if not hipins:
            logger.debug("No HIPINS in BPD, assuming TAN required for %s", segment_type)
            return True

        # Check if this transaction requires TAN
        if hasattr(hipins, "parameter") and hasattr(
            hipins.parameter, "transaction_tans_required"
        ):
            for req in hipins.parameter.transaction_tans_required:
                if req.transaction == segment_type:
                    return req.tan_required

        logger.debug(
            "Segment %s not in HIPINS transaction list, assuming TAN required",
            segment_type,
        )
        return True

    def _build_hktan_for_segment(self, segment_type: str) -> Any | None:
        hitans = _find_highest_hitans(self._parameters.bpd.segments)
        if not hitans:
            logger.warning("No HITANS in BPD, cannot build HKTAN")
            return None

        hktan_class, hktan_version = _get_hktan_class(hitans.header.version)
        if not hktan_class:
            logger.warning("No supported HKTAN version found")
            return None

        hktan = hktan_class(tan_process="4")
        if hktan_version >= 6 and hasattr(hktan, "segment_type"):
            hktan.segment_type = segment_type
        return hktan

    def _handle_decoupled_tan(
        self,
        init_response: ProcessedResponse,
        timeout: float = 120.0,
        poll_interval: float = 2.0,
        challenge_handler: ChallengeHandler | None = None,
    ) -> ProcessedResponse | None:
        """Poll for decoupled (app-based) TAN approval until confirmed or timed out."""
        import time

        hitan = init_response.find_segment_first("HITAN")
        if not hitan:
            logger.warning("No HITAN segment in response, cannot poll for approval")
            return None
        task_ref = getattr(hitan, "task_reference", None)
        if not task_ref:
            logger.warning("No task_reference in HITAN, cannot poll for approval")
            return None
        if challenge_handler is not None:
            challenge = FinTSChallenge(hitan)
            result = challenge_handler.present_challenge(challenge)
            if result.cancelled:
                raise ValueError("User cancelled the TAN challenge")
            if result.error:
                raise ValueError(f"Challenge handler error: {result.error}")

        hitans = _find_highest_hitans(self._parameters.bpd.segments)
        if not hitans:
            logger.warning("No HITANS in BPD, cannot build status HKTAN")
            return None

        hktan_class, _ = _get_hktan_class(hitans.header.version)
        if not hktan_class:
            logger.warning("No supported HKTAN version found for polling")
            return None

        max_attempts = int(timeout / poll_interval)
        attempts = 0

        logger.info(
            "Polling for decoupled TAN approval (timeout=%ss, interval=%ss)",
            timeout,
            poll_interval,
        )

        while attempts < max_attempts:
            if attempts > 0:
                time.sleep(poll_interval)
            attempts += 1
            status_hktan = hktan_class(tan_process="S")
            if hasattr(status_hktan, "task_reference"):
                status_hktan.task_reference = task_ref
            if hasattr(status_hktan, "further_tan_follows"):
                status_hktan.further_tan_follows = False
            logger.debug("Poll attempt %d: sending HKTAN status query", attempts)
            response = self._send_segments([status_hktan], internal=True)
            # 3956 = still waiting; 0010/0020 = success.
            if response.get_response_by_code("3956"):
                logger.debug("Poll attempt %d: still waiting for approval", attempts)
                continue
            if response.has_errors:
                error_resp = next(
                    (r for r in response.all_responses if r.is_error), None
                )
                err_text = error_resp.text if error_resp else "Unknown error"
                logger.error("Decoupled TAN polling failed: %s", err_text)
                # Common error: "Die Nachricht enthält Fehler" means bank timeout
                if (
                    "Nachricht enthält Fehler" in err_text
                    or "message" in err_text.lower()
                ):
                    raise TimeoutError(
                        "The bank's TAN request expired. Please try again and approve "
                        "the request in your banking app before it times out."
                    )
                raise ValueError(f"Decoupled TAN rejected: {err_text}")

            logger.info("Decoupled TAN approved after %d attempts", attempts)
            return response

        # Timeout
        raise TimeoutError(
            f"Decoupled TAN not approved within {timeout}s. "
            "Please approve the request in your banking app."
        )

    def end(self) -> None:
        if not self._state.is_open:
            return
        try:
            self._send_segments(
                [HKEND1(dialog_id=self._state.dialog_id)], internal=True
            )
        finally:
            self._state.is_open = False

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

        # Create minimal dialog context for message
        class MinimalContext:
            def __init__(ctx_self):
                ctx_self.bank_identifier = self._config.bank_identifier
                ctx_self.user_id = self._config.user_id
                ctx_self.system_id = self._config.system_id

            @property
            def client(ctx_self):
                return ctx_self

        context = MinimalContext()
        message = FinTSCustomerMessage(dialog=context)
        message += HNHBK3(
            message_size=0,
            hbci_version=300,
            dialog_id=self._state.dialog_id,
            message_number=self._state.message_number,
        )

        return message


class DialogFactory:
    """Factory for creating and managing FinTS dialogs."""

    def __init__(
        self,
        connection_config: ConnectionConfig | str,
        dialog_config: DialogConfig,
        parameters: ParameterStore,
        enc_mechanism_factory=None,
        auth_mechanism_factory=None,
    ) -> None:
        if isinstance(connection_config, str):
            connection_config = ConnectionConfig(url=connection_config)
        self._connection_config = connection_config
        self._dialog_config = dialog_config
        self._parameters = parameters
        self._enc_factory = enc_mechanism_factory
        self._auth_factory = auth_mechanism_factory

    def _create_dialog_with_connection(self) -> tuple[Dialog, HTTPSDialogConnection]:
        """Create a dialog and its connection."""
        connection = HTTPSDialogConnection(self._connection_config)

        enc_mech = self._enc_factory() if self._enc_factory else None
        auth_mechs = self._auth_factory() if self._auth_factory else []

        dialog = Dialog(
            connection=connection,
            config=self._dialog_config,
            parameters=self._parameters,
            enc_mechanism=enc_mech,
            auth_mechanisms=auth_mechs,
        )
        return dialog, connection

    @contextmanager
    def open_dialog(
        self,
        lazy_init: bool = False,
        extra_init_segments: Sequence = (),
        decoupled_timeout: float = 120.0,
        decoupled_poll_interval: float = 2.0,
    ) -> Iterator[Dialog]:
        dialog, connection = self._create_dialog_with_connection()

        try:
            if not lazy_init:
                dialog.initialize(
                    extra_init_segments,
                    decoupled_timeout=decoupled_timeout,
                    decoupled_poll_interval=decoupled_poll_interval,
                )
            yield dialog
        finally:
            if dialog.is_open:
                try:
                    dialog.end()
                except Exception:
                    logger.exception("Error closing dialog")
            connection.close()

    def create_dialog(self) -> Dialog:
        """Create an uninitialized dialog (caller manages lifecycle)."""
        dialog, _ = self._create_dialog_with_connection()
        return dialog
