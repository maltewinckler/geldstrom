"""FinTS adapter for TAN methods discovery."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from geldstrom.domain.connection import ChallengeHandler, TANConfig
from geldstrom.domain.model.tan import TANMethod, TANMethodType
from geldstrom.domain.ports.tan_methods import TANMethodsPort
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.dialog import (
    ConnectionConfig,
    Dialog,
    DialogConfig,
    HTTPSDialogConnection,
    SecurityContext,
    StandaloneAuthenticationMechanism,
    StandaloneEncryptionMechanism,
)
from geldstrom.infrastructure.fints.protocol import (
    HKSYN3,
    BankIdentifier,
    ParameterStore,
    SynchronizationMode,
)
from geldstrom.infrastructure.fints.protocol.segments.pintan import TwoStepParameters7
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import SYSTEM_ID_UNASSIGNED, FinTSConnectionHelper

logger = logging.getLogger(__name__)


class FinTSTANMethodsAdapter(TANMethodsPort):
    """FinTS 3.0 implementation of TANMethodsPort via HITANS segments in BPD."""

    def __init__(
        self,
        credentials: GatewayCredentials,
        *,
        tan_config: TANConfig | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        self._credentials = credentials
        self._tan_config = tan_config or TANConfig()
        self._challenge_handler = challenge_handler

    def get_tan_methods(
        self,
        state: FinTSSessionState | None = None,
    ) -> Sequence[TANMethod]:
        if state and state.client_blob:
            helper = FinTSConnectionHelper(
                self._credentials,
                tan_config=self._tan_config,
                challenge_handler=self._challenge_handler,
            )
            parameters = helper._build_parameters(state)
            methods = self._extract_tan_methods(parameters)
            if methods:
                logger.debug("Extracted %d TAN methods from cached BPD", len(methods))
                return methods

        logger.info("Fetching TAN methods via sync dialog (no TAN required)")
        return self._fetch_tan_methods_via_sync()

    def _fetch_tan_methods_via_sync(self) -> list[TANMethod]:
        creds = self._credentials
        bank_id = BankIdentifier(
            country_identifier=BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC.get("DE", "280"),
            bank_code=creds.route.bank_code,
        )

        connection_config = ConnectionConfig(
            url=creds.server_url,
            timeout=30.0,
        )
        connection = HTTPSDialogConnection(connection_config)
        parameters = ParameterStore()
        dialog_config = DialogConfig(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            customer_id=creds.customer_id or creds.user_id,
            system_id=SYSTEM_ID_UNASSIGNED,
            product_name=creds.product_id,
            product_version=creds.product_version,
        )

        security_context = SecurityContext(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            system_id=SYSTEM_ID_UNASSIGNED,
        )
        # Use one-step auth (security_function=999) — no TAN required.
        security_function = "999"
        enc_mechanism = StandaloneEncryptionMechanism(
            security_context,
            security_method_version=1,
        )
        auth_mechanism = StandaloneAuthenticationMechanism(
            context=security_context,
            pin=str(creds.pin),
            security_function=security_function,
        )

        sync_dialog = Dialog(
            connection=connection,
            config=dialog_config,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=[auth_mechanism],
            security_function=security_function,
        )

        try:
            sync_dialog.initialize(
                extra_segments=[
                    HKSYN3(synchronization_mode=SynchronizationMode.NEW_SYSTEM_ID)
                ]
            )

            logger.info(
                "Sync dialog complete: BPD v%d with %d segments",
                parameters.bpd_version,
                len(parameters.bpd.segments.segments),
            )

            return self._extract_tan_methods(parameters)

        finally:
            if sync_dialog.is_open:
                try:
                    sync_dialog.end()
                except Exception:
                    logger.exception("Error closing sync dialog")
            connection.close()

    def _extract_tan_methods(self, parameters: ParameterStore) -> list[TANMethod]:
        methods: list[TANMethod] = []
        seen_codes: set[str] = set()
        for segment in parameters.bpd.segments.find_segments("HITANS"):
            if not hasattr(segment, "parameter"):
                continue
            param = segment.parameter
            if not hasattr(param, "twostep_parameters"):
                continue
            for tsp in param.twostep_parameters:
                method = self._convert_twostep_params(tsp)
                if method and method.code not in seen_codes:
                    seen_codes.add(method.code)
                    methods.append(method)
        logger.info("Found %d TAN methods in BPD", len(methods))
        return methods

    def _convert_twostep_params(self, tsp: Any) -> TANMethod | None:
        try:
            security_function = getattr(tsp, "security_function", None)
            if not security_function:
                return None
            name = getattr(tsp, "name", None) or "Unknown"
            method_type = self._classify_method_type(tsp)
            is_decoupled = False
            decoupled_max_polls = None
            decoupled_first_poll = None
            decoupled_poll_interval = None

            if isinstance(tsp, TwoStepParameters7):
                max_polls = getattr(tsp, "decoupled_max_poll_number", None)
                if max_polls and max_polls > 0:
                    is_decoupled = True
                    decoupled_max_polls = max_polls
                    decoupled_first_poll = getattr(tsp, "wait_before_first_poll", None)
                    decoupled_poll_interval = getattr(
                        tsp, "wait_before_next_poll", None
                    )
                    method_type = TANMethodType.DECOUPLED

            return TANMethod(
                code=str(security_function),
                name=name,
                method_type=method_type,
                technical_id=getattr(tsp, "technical_id", None),
                zka_id=getattr(tsp, "zka_id", None),
                zka_version=getattr(tsp, "zka_version", None),
                max_tan_length=getattr(tsp, "max_length_input", None),
                is_decoupled=is_decoupled,
                decoupled_max_polls=decoupled_max_polls,
                decoupled_first_poll_delay=decoupled_first_poll,
                decoupled_poll_interval=decoupled_poll_interval,
                supports_cancel=bool(getattr(tsp, "cancel_allowed", False)),
                supports_multiple_tan=bool(
                    getattr(tsp, "multiple_tans_allowed", False)
                ),
            )
        except Exception as e:
            logger.warning("Failed to convert TAN parameters: %s", e)
            return None

    def _classify_method_type(self, tsp: Any) -> TANMethodType:
        zka_id = getattr(tsp, "zka_id", "") or ""
        tech_id = getattr(tsp, "technical_id", "") or ""
        name = (getattr(tsp, "name", "") or "").lower()

        zka_lower = zka_id.lower()
        tech_lower = tech_id.lower()
        if "pushtan" in zka_lower or "push" in name:
            return TANMethodType.PUSH
        if "mobiletan" in zka_lower or "sms" in name or "mtan" in name:
            return TANMethodType.SMS
        if "chiptan" in zka_lower or "chip" in name or "flickercode" in name:
            return TANMethodType.CHIPTAN
        if "phototan" in zka_lower or "photo" in name or "qr" in name:
            return TANMethodType.PHOTO_TAN

        # Check technical ID patterns
        if "decoupled" in tech_lower:
            return TANMethodType.DECOUPLED

        return TANMethodType.UNKNOWN


__all__ = ["FinTSTANMethodsAdapter"]
