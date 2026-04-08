"""FinTS 3.0 metadata service — connection management and TAN method discovery."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from geldstrom.infrastructure.fints.protocol import ParameterStore
from geldstrom.infrastructure.fints.protocol.segments.pintan import TwoStepParameters7
from geldstrom.infrastructure.fints.session import FinTSSessionState
from geldstrom.infrastructure.fints.support.connection import (
    build_parameters_from_state,
)
from geldstrom.infrastructure.fints.tan import TANMethod

from .base import FinTSServiceBase

logger = logging.getLogger(__name__)


class FinTSMetadataService(FinTSServiceBase):
    """Manages FinTS connections for bank metadata (TAN methods) via HITANS segments in BPD."""

    def get_tan_methods(
        self,
        state: FinTSSessionState | None = None,
    ) -> Sequence[TANMethod]:
        if state and state.client_blob:
            parameters = build_parameters_from_state(state)
            methods = self._extract_tan_methods(parameters)
            if methods:
                logger.debug("Extracted %d TAN methods from cached BPD", len(methods))
                return methods

        logger.info("Fetching TAN methods via sync dialog (no TAN required)")
        return self._fetch_tan_methods_via_sync()

    def _fetch_tan_methods_via_sync(self) -> list[TANMethod]:
        helper = self._make_helper()
        with helper.connect_sync() as ctx:
            logger.info(
                "Sync dialog complete: BPD v%d with %d segments",
                ctx.parameters.bpd_version,
                len(ctx.parameters.bpd.segments.segments),
            )
            return self._extract_tan_methods(ctx.parameters)

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

            return TANMethod(
                code=str(security_function),
                name=name,
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


__all__ = ["FinTSMetadataService"]
