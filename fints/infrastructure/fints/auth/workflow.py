"""PIN/TAN workflow orchestration for FinTS dialogs."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping, Sequence

from fints.constants import ING_BANK_IDENTIFIER, SYSTEM_ID_UNASSIGNED
from fints.exceptions import (
    FinTSClientError,
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSSCARequiredError,
)
from fints.formals import DescriptionRequired, KTI1, TANMediaClass4, TANMediaType2

from .challenge import NeedTANResponse
from .mechanisms import (
    PinTanDummyEncryptionMechanism,
    PinTanOneStepAuthenticationMechanism,
    PinTanTwoStepAuthenticationMechanism,
)

if TYPE_CHECKING:
    from fints.client import FinTS3PinTanClient

# Mapping of HKTAN versions to segment classes
IMPLEMENTED_HKTAN_VERSIONS: Mapping[int, type] = {}

# Populated at module load
def _init_hktan_versions():
    from fints.segments.auth import HKTAN2, HKTAN3, HKTAN5, HKTAN6, HKTAN7
    global IMPLEMENTED_HKTAN_VERSIONS
    IMPLEMENTED_HKTAN_VERSIONS = {
        2: HKTAN2,
        3: HKTAN3,
        5: HKTAN5,
        6: HKTAN6,
        7: HKTAN7,
    }

_init_hktan_versions()


@dataclass
class TanWorkflowConfig:
    """Configuration for TAN workflow behavior."""

    selected_security_function: str | None = None
    selected_tan_medium: str | None = None
    allowed_security_functions: list[str] = field(default_factory=list)


class PinTanWorkflow:
    """
    Orchestrates TAN requirements and message sending for PIN/TAN dialogs.

    This class manages:
    - TAN mechanism selection and configuration
    - Determining when TAN is required for operations
    - Building TAN request segments
    - Handling TAN responses and retries
    """

    def __init__(
        self,
        owner: "FinTS3PinTanClient",
        *,
        selected_security_function: str | None = None,
        selected_tan_medium: str | None = None,
        allowed_security_functions: Sequence[str] | None = None,
        init_tan_response=None,
    ) -> None:
        self._owner = owner
        self._pending_tan: str | None = None
        self._bootstrap_mode = True
        self._selected_security_function = selected_security_function
        self._selected_tan_medium = selected_tan_medium
        self._allowed_security_functions = list(allowed_security_functions or [])
        self._init_tan_response = init_tan_response

    # --- State properties ---

    @property
    def selected_security_function(self) -> str | None:
        return self._selected_security_function

    @selected_security_function.setter
    def selected_security_function(self, value: str | None) -> None:
        self._selected_security_function = value

    @property
    def allowed_security_functions(self) -> list[str]:
        return self._allowed_security_functions

    @allowed_security_functions.setter
    def allowed_security_functions(self, functions: Sequence[str] | None) -> None:
        self._allowed_security_functions = list(functions or [])

    @property
    def selected_tan_medium(self) -> str | None:
        return self._selected_tan_medium

    @selected_tan_medium.setter
    def selected_tan_medium(self, value: str | None) -> None:
        self._selected_tan_medium = value

    @property
    def init_tan_response(self):
        return self._init_tan_response

    @init_tan_response.setter
    def init_tan_response(self, value) -> None:
        self._init_tan_response = value

    # --- TAN mechanism management ---

    def get_tan_mechanisms(self) -> OrderedDict:
        """Return available TAN mechanisms from BPD."""
        owner = self._owner
        retval = OrderedDict()
        for version in sorted(IMPLEMENTED_HKTAN_VERSIONS.keys()):
            for seg in owner.bpd.find_segments("HITANS", version):
                for param in seg.parameter.twostep_parameters:
                    if param.security_function in self._allowed_security_functions:
                        retval[param.security_function] = param
        return retval

    def get_current_tan_mechanism(self) -> str | None:
        """Return currently selected TAN mechanism."""
        return self.selected_security_function

    def set_tan_mechanism(self, security_function: str) -> None:
        """Set the TAN mechanism to use."""
        owner = self._owner
        if owner._standing_dialog:
            raise Exception("Cannot change TAN mechanism with a standing dialog")
        self.selected_security_function = security_function

    def set_tan_medium(self, tan_medium) -> None:
        """Set the TAN medium (device) to use."""
        owner = self._owner
        if owner._standing_dialog:
            raise Exception("Cannot change TAN medium with a standing dialog")
        if tan_medium is None:
            medium_name = None
        elif hasattr(tan_medium, "tan_medium_name"):
            medium_name = tan_medium.tan_medium_name
        else:
            medium_name = tan_medium
        self.selected_tan_medium = medium_name

    # --- Pending TAN management ---

    def store_pending_tan(self, tan: str) -> None:
        """Store a TAN for the next signed message."""
        self._pending_tan = tan

    def consume_pending_tan(self) -> str | None:
        """Consume and return the pending TAN."""
        tan = self._pending_tan
        self._pending_tan = None
        return tan

    # --- State persistence ---

    def restore_state(self, data: Mapping) -> None:
        """Restore workflow state from serialized data."""
        self.selected_tan_medium = data.get(
            "selected_tan_medium", self.selected_tan_medium
        )
        self.selected_security_function = data.get(
            "selected_security_function", self.selected_security_function
        )
        self.allowed_security_functions = data.get(
            "allowed_security_functions", self.allowed_security_functions
        )

    def dump_state(self, data: dict, including_private: bool = False) -> dict:
        """Dump workflow state for serialization."""
        data.update(
            {
                "selected_security_function": self.selected_security_function,
                "selected_tan_medium": self.selected_tan_medium,
            }
        )
        if including_private:
            data["allowed_security_functions"] = self.allowed_security_functions
        return data

    # --- Dialog mechanisms ---

    def dialog_mechanisms(self):
        """Create encryption and auth mechanisms for dialog."""
        owner = self._owner
        if owner.pin is None:
            return None, []

        current = self.selected_security_function
        if not current or current == "999":
            enc = PinTanDummyEncryptionMechanism(1)
            auth = [PinTanOneStepAuthenticationMechanism(owner.pin)]
        else:
            enc = PinTanDummyEncryptionMechanism(2)
            auth = [
                PinTanTwoStepAuthenticationMechanism(
                    owner, current, owner.pin
                )
            ]
        return enc, auth

    def fetch_tan_mechanisms(self) -> str | None:
        """Fetch available TAN mechanisms from bank."""
        owner = self._owner
        if (
            owner.system_id
            and owner.system_id != SYSTEM_ID_UNASSIGNED
            and not self.get_current_tan_mechanism()
        ):
            self.set_tan_mechanism("999")
            with owner._get_dialog(lazy_init=True) as dialog:
                response = dialog.init()
                owner.process_response_message(dialog, response, internal_send=True)
        else:
            self.set_tan_mechanism("999")
            owner._ensure_system_id()

        if self.get_current_tan_mechanism():
            return self.get_current_tan_mechanism()

        with owner._new_dialog():
            return self.get_current_tan_mechanism()

    # --- TAN requirement checks ---

    def need_twostep_tan(self, segment) -> bool:
        """Check if segment requires two-step TAN."""
        from fints.segments.auth import HIPINS1

        current = self.get_current_tan_mechanism()
        if not current or current == "999":
            return False

        hipins = self._owner.bpd.find_segment_first(HIPINS1)
        if not hipins:
            return False

        for req in hipins.parameter.transaction_tans_required:
            if segment.header.type == req.transaction:
                return req.tan_required
        return False

    def is_challenge_structured(self) -> bool:
        """Check if current mechanism uses structured challenges."""
        param = self.get_tan_mechanisms()[self.get_current_tan_mechanism()]
        if hasattr(param, "challenge_structured"):
            return param.challenge_structured
        return False

    def is_media_required(self) -> bool:
        """Check if TAN medium selection is required."""
        owner = self._owner
        if owner.bank_identifier == ING_BANK_IDENTIFIER:
            return False
        tan_mechanism = self.get_tan_mechanisms()[self.get_current_tan_mechanism()]
        supported_media = getattr(tan_mechanism, "supported_media_number", None)
        return (
            supported_media is not None
            and supported_media > 1
            and tan_mechanism.description_required == DescriptionRequired.MUST
        )

    # --- TAN segment building ---

    def build_tan_segment(self, orig_seg, tan_process: str, tan_seg=None):
        """Build HKTAN segment for the given TAN process."""
        tan_mechanisms = self.get_tan_mechanisms()
        tan_mechanism = tan_mechanisms[self.get_current_tan_mechanism()]
        hktan = IMPLEMENTED_HKTAN_VERSIONS.get(tan_mechanism.VERSION)

        seg = hktan(tan_process=tan_process)

        if tan_process == "1":
            seg.segment_type = orig_seg.header.type
            account_ = getattr(orig_seg, "account", None)
            if isinstance(account_, KTI1):
                seg.account = account_
            raise NotImplementedError("TAN-Process 1 not implemented")

        if tan_process in ("1", "3", "4") and self.is_media_required():
            seg.tan_medium_name = self.selected_tan_medium or ""

        if tan_process == "4" and tan_mechanism.VERSION >= 6:
            seg.segment_type = orig_seg.header.type

        if tan_process in ("2", "3", "S") and tan_seg is not None:
            seg.task_reference = tan_seg.task_reference

        if tan_process in ("1", "2", "S"):
            seg.further_tan_follows = False

        return seg

    # --- Message sending with TAN handling ---

    def send_with_possible_retry(self, dialog, command_seg, resume_func):
        """Send command, handling TAN requirement if needed."""
        with dialog:
            if self.need_twostep_tan(command_seg):
                tan_seg = self.build_tan_segment(command_seg, "4")
                response = dialog.send(command_seg, tan_seg)

                for resp in response.responses(tan_seg):
                    if resp.code in ("0030", "3955"):
                        return NeedTANResponse(
                            command_seg,
                            response.find_segment_first("HITAN"),
                            resume_func,
                            self.is_challenge_structured(),
                            resp.code == "3955",
                        )
                    if resp.code.startswith("9"):
                        raise FinTSClientError(f"Error response: {response!r}")
            else:
                response = dialog.send(command_seg)

            return resume_func(command_seg, response)

    def send_tan(self, challenge: NeedTANResponse, tan: str):
        """Send TAN response for a challenge."""
        owner = self._owner
        with owner._get_dialog() as dialog:
            if challenge.decoupled:
                tan_seg = self.build_tan_segment(
                    challenge.command_seg, "S", challenge.tan_request
                )
            else:
                tan_seg = self.build_tan_segment(
                    challenge.command_seg, "2", challenge.tan_request
                )
                self.store_pending_tan(tan)

            response = dialog.send(tan_seg)

            if challenge.decoupled:
                status_segment = response.find_segment_first("HITAN")
                if not status_segment:
                    raise FinTSClientError("No TAN status received.")
                for resp in response.responses(tan_seg):
                    if resp.code == "3956":
                        return NeedTANResponse(
                            challenge.command_seg,
                            challenge.tan_request,
                            challenge.resume_method,
                            challenge.tan_request_structured,
                            challenge.decoupled,
                        )

            # resume_method can be a string (method name) or a callable (closure)
            if callable(challenge.resume_method):
                resume_func = challenge.resume_method
            else:
                resume_func = getattr(owner, challenge.resume_method)
            return resume_func(challenge.command_seg, response)

    # --- Response handling ---

    def handle_response(self, dialog, segment, response) -> None:
        """Handle response codes that affect TAN workflow state."""
        owner = self._owner

        if response.code == "3920" and owner.bank_identifier != ING_BANK_IDENTIFIER:
            self.allowed_security_functions = list(response.parameters)
            current = self.get_current_tan_mechanism()
            if current is None or current not in self.allowed_security_functions:
                for sf, param in self.get_tan_mechanisms().items():
                    if sf == "999":
                        continue
                    if param.tan_process != "2":
                        continue
                    try:
                        self.set_tan_mechanism(param.security_function)
                        break
                    except NotImplementedError:
                        pass
                else:
                    self.set_tan_mechanism("999")

        if response.code == "9010":
            raise FinTSClientError(
                "Error during dialog initialization, could not fetch BPD. "
                "Please check that you passed the correct bank identifier."
            )

        dialog_pin_failure = (
            not dialog.open
            and response.code.startswith("9")
            and not self._bootstrap_mode
        )
        pin_error = dialog_pin_failure or response.code in {
            "9340", "9910", "9930", "9931", "9942"
        }
        if pin_error:
            if owner.pin:
                owner.pin.block()
            raise FinTSClientPINError("Error during dialog initialization, PIN wrong?")

        if response.code == "3938":
            if owner.pin:
                owner.pin.block()
            raise FinTSClientTemporaryAuthError("Account is temporarily locked.")

        if response.code == "9075":
            if self._bootstrap_mode:
                if owner._standing_dialog:
                    owner._standing_dialog.open = False
            else:
                raise FinTSSCARequiredError(
                    "This operation requires strong customer authentication."
                )

    # --- TAN media discovery ---

    def get_tan_media(
        self,
        media_type: TANMediaType2 = TANMediaType2.ALL,
        media_class: TANMediaClass4 = TANMediaClass4.ALL,
    ):
        """Get available TAN media from bank."""
        from fints.segments.auth import HKTAB4, HKTAB5

        owner = self._owner
        if owner.connection.url == "https://hbci.postbank.de/banking/hbci.do":
            context = owner._new_dialog(lazy_init=True)
            method_name = "init"
        else:
            context = owner._get_dialog()
            method_name = "send"

        with context as dialog:
            if isinstance(self.init_tan_response, NeedTANResponse):
                from fints.formals import TANUsageOption
                return TANUsageOption.ALL_ACTIVE, []

            hktab = owner._find_highest_supported_command(HKTAB4, HKTAB5)
            seg = hktab(
                tan_media_type=media_type,
                tan_media_class=str(media_class),
            )

            try:
                self._bootstrap_mode = True
                response = getattr(dialog, method_name)(seg)
            finally:
                self._bootstrap_mode = False

            for resp in response.response_segments(seg, "HITAB"):
                return resp.tan_usage_option, list(resp.tan_media_list)

        return None, []


__all__ = [
    "IMPLEMENTED_HKTAN_VERSIONS",
    "PinTanWorkflow",
    "TanWorkflowConfig",
]

