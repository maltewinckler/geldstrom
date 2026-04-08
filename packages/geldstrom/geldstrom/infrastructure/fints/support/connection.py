"""Shared connection helper for FinTS infrastructure."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from geldstrom.infrastructure.fints.challenge import (
    ChallengeHandler,
    DecoupledTANPending,
    TANConfig,
)
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.dialog import (
    SYSTEM_ID_UNASSIGNED,
    ConnectionConfig,
    DecoupledTanStrategy,
    Dialog,
    DialogConfig,
    DialogSnapshot,
    HTTPSDialogConnection,
    NoTanStrategy,
    SecurityContext,
    StandaloneAuthenticationMechanism,
    StandaloneEncryptionMechanism,
)
from geldstrom.infrastructure.fints.protocol import (
    HISYN4,
    HKSYN3,
    HKTAN_VERSIONS,
    BankIdentifier,
    ParameterStore,
    SynchronizationMode,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState
from geldstrom.infrastructure.fints.support.serialization import (
    compress_datablob,
    decompress_datablob,
)

# Magic bytes for the compressed data blob format
DATA_BLOB_MAGIC = b"python-fints"

logger = logging.getLogger(__name__)


def build_parameters_from_state(
    state: FinTSSessionState | None,
) -> ParameterStore:
    """Restore ParameterStore from serialized session state."""
    if state and state.client_blob:
        try:
            data = _extract_params_dict(state.client_blob)
            if data:
                logger.debug(
                    "Restored params dict: bpd_bin=%s bytes, upd_bin=%s bytes",
                    len(data.get("bpd_bin", b"") or b""),
                    len(data.get("upd_bin", b"") or b""),
                )
                return ParameterStore.from_dict(data)
        except Exception as e:
            import traceback

            logger.warning(
                "Failed to restore parameters from state: %s\n%s",
                e,
                traceback.format_exc(),
            )

    return ParameterStore()


def _extract_params_dict(
    client_blob: bytes | Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Extract parameter dictionary from client blob (bytes or dict)."""
    if isinstance(client_blob, dict):
        return client_blob
    if isinstance(client_blob, bytes):
        try:
            _version, data = decompress_datablob(DATA_BLOB_MAGIC, client_blob)
            return data
        except (ValueError, Exception) as e:
            logger.debug("Failed to decompress blob: %s", e)
            return None

    return None


@dataclass
class ConnectionContext:
    """Active dialog context for FinTS operations."""

    dialog: Dialog
    parameters: ParameterStore
    credentials: GatewayCredentials
    system_id: str
    connection: HTTPSDialogConnection | None = None
    detached: bool = False

    def detach(self) -> None:
        self.detached = True


class FinTSConnectionHelper:
    """Creates and manages FinTS dialog connections."""

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

    @contextmanager
    def connect(
        self,
        state: FinTSSessionState | None = None,
    ) -> Iterator[ConnectionContext]:
        creds = self._credentials
        bank_id = BankIdentifier(
            country_identifier=BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC.get(
                creds.route.country_code, "280"
            ),
            bank_code=creds.route.bank_code,
        )
        system_id = state.system_id if state else SYSTEM_ID_UNASSIGNED
        parameters = self._build_parameters(state)
        connection_config = ConnectionConfig(
            url=creds.server_url,
            timeout=30.0,
        )
        connection = HTTPSDialogConnection(connection_config)
        # Phase 1: obtain system ID via sync dialog if not already known.
        if system_id == SYSTEM_ID_UNASSIGNED:
            system_id = self._ensure_system_id(connection, bank_id, parameters, creds)
            connection.close()
            connection = HTTPSDialogConnection(connection_config)
        # Phase 2: open main dialog.
        dialog, extra_init_segments = self._create_main_dialog(
            connection, bank_id, system_id, parameters, creds
        )

        _detached = False
        ctx = ConnectionContext(
            dialog=dialog,
            parameters=parameters,
            credentials=creds,
            system_id=system_id,
            connection=connection,
        )

        try:
            dialog.initialize(
                extra_segments=extra_init_segments,
                challenge_handler=self._challenge_handler,
            )

            yield ctx

        except DecoupledTANPending as pending:
            ctx.detach()
            _detached = True
            pending.context = ctx
            raise

        finally:
            if not _detached:
                if dialog.is_open:
                    try:
                        dialog.end()
                    except Exception:
                        logger.exception("Error closing dialog")
                connection.close()

    def _create_main_dialog(
        self,
        connection: HTTPSDialogConnection,
        bank_id: BankIdentifier,
        system_id: str,
        parameters: ParameterStore,
        creds: GatewayCredentials,
    ) -> tuple[Dialog, list]:
        dialog_config = DialogConfig(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            customer_id=creds.customer_id or creds.user_id,
            system_id=system_id,
            product_name=creds.product_id,
            product_version=creds.product_version,
        )
        security_context = SecurityContext(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            system_id=system_id,
        )
        extra_init_segments = []

        if creds.tan_method:
            security_function = creds.tan_method
            tan_strategy = DecoupledTanStrategy(security_function)
            logger.info(
                "Using two-step TAN: security_function=%s, tan_medium=%s",
                security_function,
                creds.tan_medium,
            )

            hktan = self._build_hktan_for_init(parameters)
            if hktan:
                extra_init_segments.append(hktan)
        else:
            security_function = "999"
            tan_strategy = NoTanStrategy()

        # HNVSK (encryption) uses security_method_version=2 for two-step TAN,
        # HNSHK (signature) uses version=1.
        enc_version = 2 if creds.tan_method else 1
        enc_mechanism = StandaloneEncryptionMechanism(
            security_context,
            security_method_version=enc_version,
        )
        auth_mechanism = StandaloneAuthenticationMechanism(
            context=security_context,
            pin=str(creds.pin),
            security_function=security_function,
        )

        dialog = Dialog(
            connection=connection,
            config=dialog_config,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=[auth_mechanism],
            tan_strategy=tan_strategy,
        )

        return dialog, extra_init_segments

    def _build_hktan_for_init(
        self,
        parameters: ParameterStore,
    ) -> Any:
        """Build HKTAN segment (tan_process='4') for dialog initialization.

        NOTE: tan_medium_name must be None — setting it causes bank error 9110.
        """
        hitans = None
        for seg in parameters.bpd.segments.find_segments("HITANS"):
            if hitans is None or seg.header.version > hitans.header.version:
                hitans = seg

        if not hitans:
            logger.warning("No HITANS in BPD, cannot build HKTAN")
            return None

        hktan_version = hitans.header.version
        hktan_class = HKTAN_VERSIONS.get(hktan_version)
        if not hktan_class:
            logger.warning(
                "HKTAN version %d not directly supported, trying lower", hktan_version
            )
            # Try to find a supported version
            for v in sorted(HKTAN_VERSIONS.keys(), reverse=True):
                if v <= hktan_version:
                    hktan_class = HKTAN_VERSIONS[v]
                    hktan_version = v
                    break
        if not hktan_class:
            logger.warning("No supported HKTAN version found")
            return None

        logger.info("Building HKTAN%d for main dialog init", hktan_version)

        # Create segment with tan_process='4' (dialog initialization)
        seg = hktan_class(tan_process="4")
        if hktan_version >= 6 and hasattr(seg, "segment_type"):
            seg.segment_type = "HKIDN"
        return seg

    def _ensure_system_id(
        self,
        connection: HTTPSDialogConnection,
        bank_id: BankIdentifier,
        parameters: ParameterStore,
        creds: GatewayCredentials,
    ) -> str:
        logger.info("No system ID, requesting from bank via sync dialog...")
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
        # One-step auth (999) for sync — some banks reject two-step during identification.
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
            tan_strategy=NoTanStrategy(),
        )

        try:
            response = sync_dialog.initialize(
                extra_segments=[
                    HKSYN3(synchronization_mode=SynchronizationMode.NEW_SYSTEM_ID)
                ]
            )

            hisyn = response.find_segment_first(HISYN4)
            if not hisyn or not hisyn.system_id:
                raise ValueError("Could not obtain system ID from bank")

            system_id = hisyn.system_id
            logger.info("Obtained system ID: %s", system_id)
            logger.info(
                "BPD version after sync: %d, %d segments",
                parameters.bpd_version,
                len(parameters.bpd.segments.segments),
            )

            return system_id

        finally:
            if sync_dialog.is_open:
                try:
                    sync_dialog.end()
                except Exception:
                    logger.exception("Error closing sync dialog")

    def _build_parameters(
        self,
        state: FinTSSessionState | None,
    ) -> ParameterStore:
        return build_parameters_from_state(state)

    @contextmanager
    def connect_sync(
        self,
        extra_segments: list | None = None,
    ) -> Iterator[ConnectionContext]:
        """Open a one-step sync dialog (security_function=999, no TAN).

        Useful for BPD/TAN-method discovery and system-ID acquisition.
        """
        creds = self._credentials
        bank_id = BankIdentifier(
            country_identifier=BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC.get(
                creds.route.country_code, "280"
            ),
            bank_code=creds.route.bank_code,
        )
        parameters = ParameterStore()
        connection_config = ConnectionConfig(
            url=creds.server_url,
            timeout=30.0,
        )
        connection = HTTPSDialogConnection(connection_config)
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
        enc_mechanism = StandaloneEncryptionMechanism(
            security_context,
            security_method_version=1,
        )
        auth_mechanism = StandaloneAuthenticationMechanism(
            context=security_context,
            pin=str(creds.pin),
            security_function="999",
        )
        sync_dialog = Dialog(
            connection=connection,
            config=dialog_config,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=[auth_mechanism],
            tan_strategy=NoTanStrategy(),
        )
        ctx = ConnectionContext(
            dialog=sync_dialog,
            parameters=parameters,
            credentials=creds,
            system_id=SYSTEM_ID_UNASSIGNED,
            connection=connection,
        )
        try:
            sync_dialog.initialize(
                extra_segments=extra_segments
                or [HKSYN3(synchronization_mode=SynchronizationMode.NEW_SYSTEM_ID)],
            )
            yield ctx
        finally:
            if sync_dialog.is_open:
                try:
                    sync_dialog.end()
                except Exception:
                    logger.exception("Error closing sync dialog")
            connection.close()

    def resume_for_polling(
        self,
        snapshot: DialogSnapshot,
        fints_session_state: bytes,
        server_url: str,
    ) -> ConnectionContext:
        """Reconstruct a ``ConnectionContext`` for decoupled TAN polling.

        Uses fresh credentials from ``self._credentials`` (provided by the
        client on each poll request) combined with the serialised dialog
        snapshot that was captured when the TAN challenge was first raised.
        The returned context contains a ``Dialog`` ready for
        ``poll_decoupled_once()``.
        """
        from geldstrom.infrastructure.fints.session import FinTSSessionState

        state = FinTSSessionState.deserialize(fints_session_state)
        parameters = build_parameters_from_state(state)
        system_id = snapshot.system_id

        creds = self._credentials
        bank_id = BankIdentifier(
            country_identifier=snapshot.country_identifier,
            bank_code=snapshot.bank_code or None,
        )
        connection_config = ConnectionConfig(url=server_url, timeout=30.0)
        connection = HTTPSDialogConnection(connection_config)

        security_context = SecurityContext(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            system_id=system_id,
        )
        enc_mechanism = StandaloneEncryptionMechanism(
            security_context,
            security_method_version=2,
        )
        auth_mechanism = StandaloneAuthenticationMechanism(
            context=security_context,
            pin=str(creds.pin),
            security_function=snapshot.security_function,
        )

        dialog = Dialog.resume(
            snapshot=snapshot,
            connection=connection,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=[auth_mechanism],
        )

        return ConnectionContext(
            dialog=dialog,
            parameters=parameters,
            credentials=creds,
            system_id=system_id,
            connection=connection,
        )

    def create_session_state(
        self,
        ctx: ConnectionContext,
    ) -> FinTSSessionState:
        params_dict = ctx.parameters.to_dict()
        params_dict["system_id"] = ctx.system_id
        client_blob = compress_datablob(DATA_BLOB_MAGIC, 1, params_dict)

        return FinTSSessionState(
            route=self._credentials.route,
            user_id=self._credentials.user_id,
            system_id=ctx.system_id,
            client_blob=client_blob,
            bpd_version=ctx.parameters.bpd_version,
            upd_version=ctx.parameters.upd_version,
        )


__all__ = ["ConnectionContext", "FinTSConnectionHelper", "build_parameters_from_state"]
