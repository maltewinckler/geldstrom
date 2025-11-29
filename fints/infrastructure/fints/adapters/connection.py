"""Shared connection helper for FinTS adapters.

This module provides a unified way to create dialog connections
with proper security mechanisms.

Key features:
- Standalone security mechanisms (no legacy client dependency)
- Two-step TAN support with HKTAN segments
- System ID synchronization
- BPD/UPD parameter management
- Decoupled TAN handling (app-based approval)
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator, Mapping

from fints.application.ports import GatewayCredentials
from fints.constants import SYSTEM_ID_UNASSIGNED
from fints.formals import BankIdentifier, CUSTOMER_ID_ANONYMOUS, SynchronizationMode
from fints.infrastructure.fints.auth.standalone_mechanisms import (
    SecurityContext,
    StandaloneAuthenticationMechanism,
    StandaloneEncryptionMechanism,
)
from fints.infrastructure.fints.dialog import (
    ConnectionConfig,
    Dialog,
    DialogConfig,
    DialogFactory,
    HTTPSDialogConnection,
)
from fints.infrastructure.fints.protocol import ParameterStore
from fints.infrastructure.fints.session import FinTSSessionState
from fints.segments.auth import HKTAN2, HKTAN6, HKTAN7
from fints.segments.dialog import HKSYN3, HISYN4
from fints.utils import Password, decompress_datablob, compress_datablob

# Magic bytes for the compressed data blob format
DATA_BLOB_MAGIC = b"python-fints"

# Mapping of HKTAN versions to segment classes
HKTAN_VERSIONS = {
    2: HKTAN2,
    6: HKTAN6,
    7: HKTAN7,
}

if TYPE_CHECKING:
    from fints.infrastructure.fints.operations import AccountOperations

logger = logging.getLogger(__name__)


@dataclass
class ConnectionContext:
    """
    Active connection context for FinTS operations.

    Provides access to dialog, parameters, and credentials needed
    for executing operations.
    """

    dialog: Dialog
    parameters: ParameterStore
    credentials: GatewayCredentials
    system_id: str


class FinTSConnectionHelper:
    """
    Helper class for creating and managing FinTS connections.

    This encapsulates the complexity of:
    - Building dialogs with proper security mechanisms
    - Managing BPD/UPD parameters
    - Handling session state serialization
    - Two-step TAN authentication

    Usage:
        helper = FinTSConnectionHelper(credentials)
        with helper.connect(state) as ctx:
            ops = AccountOperations(ctx.dialog, ctx.parameters)
            accounts = ops.fetch_sepa_accounts()
    """

    def __init__(self, credentials: GatewayCredentials) -> None:
        """
        Initialize with credentials.

        Args:
            credentials: Bank connection credentials
        """
        self._credentials = credentials

    @contextmanager
    def connect(
        self,
        state: FinTSSessionState | None = None,
    ) -> Iterator[ConnectionContext]:
        """
        Open a connection and yield a context for operations.

        The connection process:
        1. If no system ID: open sync dialog to get system ID + BPD
        2. Open main dialog with system ID (and optional HKTAN for two-step)
        3. Main dialog receives UPD if authenticated properly

        Args:
            state: Optional existing session state

        Yields:
            ConnectionContext with active dialog and parameters
        """
        creds = self._credentials

        # Build bank identifier
        bank_id = BankIdentifier(
            BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC.get("DE", "280"),
            creds.route.bank_code,
        )

        # Determine system ID
        system_id = state.system_id if state else SYSTEM_ID_UNASSIGNED

        # Build parameter store from state or empty
        parameters = self._build_parameters(state)

        # Build connection
        connection_config = ConnectionConfig(
            url=creds.server_url,
            timeout=30.0,
        )
        connection = HTTPSDialogConnection(connection_config)

        # Phase 1: If we don't have a system ID, obtain one via sync dialog
        # This also fetches initial BPD so we know which TAN mechanisms exist
        if system_id == SYSTEM_ID_UNASSIGNED:
            system_id = self._ensure_system_id(
                connection, bank_id, parameters, creds
            )
            # Close and reopen connection for main dialog
            # (legacy client creates fresh connection for each dialog)
            connection.close()
            connection = HTTPSDialogConnection(connection_config)

        # Phase 2: Open main dialog with proper authentication
        # If TAN method is configured, use two-step auth which gets UPD
        dialog, extra_init_segments = self._create_main_dialog(
            connection, bank_id, system_id, parameters, creds
        )

        try:
            # Initialize dialog - with HKTAN if using two-step auth
            init_response = dialog.initialize(extra_segments=extra_init_segments)

            # Handle decoupled TAN if required (code 3955 = app approval needed)
            if init_response.get_response_by_code("3955"):
                logger.info("Decoupled TAN required - waiting for app approval...")
                self._handle_decoupled_tan(dialog, init_response, parameters)

            yield ConnectionContext(
                dialog=dialog,
                parameters=parameters,
                credentials=creds,
                system_id=system_id,
            )

        finally:
            # Close dialog
            if dialog.is_open:
                try:
                    dialog.end()
                except Exception:
                    logger.exception("Error closing dialog")
            connection.close()

    def _handle_decoupled_tan(
        self,
        dialog: Dialog,
        init_response,
        parameters: ParameterStore,
        timeout: float = 120.0,
        poll_interval: float = 2.0,
    ) -> None:
        """
        Handle decoupled TAN approval (app-based authentication).

        When the bank returns code 3955, the user needs to approve
        in their banking app. This method polls until approval or timeout.

        Args:
            dialog: Active dialog
            init_response: Response from dialog initialization
            parameters: Parameter store to get HKTAN version from BPD
            timeout: Maximum wait time in seconds
            poll_interval: Time between poll attempts in seconds
        """
        # Find HITAN segment from init response
        hitan = init_response.find_segment_first("HITAN")
        if not hitan:
            logger.warning("No HITAN segment in response, cannot poll")
            return

        # Get the task reference from HITAN for status polling
        task_ref = getattr(hitan, "task_reference", None)
        if not task_ref:
            logger.warning("No task_reference in HITAN, cannot poll")
            return

        # Find highest supported HKTAN version
        hitans = None
        for seg in parameters.bpd.segments.find_segments("HITANS"):
            if hitans is None or seg.header.version > hitans.header.version:
                hitans = seg

        if not hitans:
            logger.warning("No HITANS in BPD, cannot build status HKTAN")
            return

        hktan_version = hitans.header.version
        hktan_class = HKTAN_VERSIONS.get(hktan_version)

        # Fall back to lower supported version
        if not hktan_class:
            for v in sorted(HKTAN_VERSIONS.keys(), reverse=True):
                if v <= hktan_version:
                    hktan_class = HKTAN_VERSIONS[v]
                    hktan_version = v
                    break

        if not hktan_class:
            logger.warning("No supported HKTAN version found for polling")
            return

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

            # Build status query HKTAN with tan_process='S'
            status_hktan = hktan_class(tan_process="S")

            # Set task reference for status polling
            if hasattr(status_hktan, "task_reference"):
                status_hktan.task_reference = task_ref

            # Required for status polling: indicate no more TANs follow
            if hasattr(status_hktan, "further_tan_follows"):
                status_hktan.further_tan_follows = False

            logger.debug(
                "Poll attempt %d: sending HKTAN status query", attempts
            )

            # Send status query (bypass HKTAN injection)
            # Use internal method to avoid auto-HKTAN injection
            response = dialog._send_segments(  # noqa: SLF001
                [status_hktan], internal=True
            )

            # Check response codes
            # 3956 = Still waiting for approval
            # 0010/0020 = Success
            if response.get_response_by_code("3956"):
                logger.debug("Poll attempt %d: still waiting", attempts)
                continue

            # No 3956 means either success or error
            if response.has_errors:
                error_resp = next(
                    (r for r in response.all_responses if r.is_error), None
                )
                err_text = error_resp.text if error_resp else "Unknown error"
                logger.error("Decoupled TAN polling failed: %s", err_text)
                raise ValueError(f"Decoupled TAN rejected: {err_text}")

            logger.info("Decoupled TAN approved after %d attempts", attempts)
            return

        # Timeout
        raise TimeoutError(
            f"Decoupled TAN not approved within {timeout}s. "
            "Please approve the login request in your banking app."
        )

    def _create_main_dialog(
        self,
        connection: HTTPSDialogConnection,
        bank_id: BankIdentifier,
        system_id: str,
        parameters: ParameterStore,
        creds: GatewayCredentials,
    ) -> tuple[Dialog, list]:
        """
        Create the main dialog with appropriate authentication.

        If a TAN method is configured in credentials, uses two-step auth
        with HKTAN segment. Otherwise uses one-step auth.

        Returns:
            Tuple of (Dialog, extra_init_segments)
        """
        # Build dialog config
        dialog_config = DialogConfig(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            customer_id=creds.customer_id or creds.user_id,
            system_id=system_id,
            product_name=creds.product_id,
            product_version=creds.product_version,
        )

        # Create security context for standalone mechanisms
        security_context = SecurityContext(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            system_id=system_id,
        )

        # Determine security function and HKTAN segment
        # IMPORTANT: The legacy client sends HKTAN with tan_process='4' in the
        # main dialog init (not sync dialog) to receive UPD from the bank.
        security_function = "999"  # Default: one-step
        extra_init_segments = []

        if creds.tan_method:
            # Two-step TAN authentication requested
            security_function = creds.tan_method
            logger.info(
                "Using two-step TAN: security_function=%s, tan_medium=%s",
                security_function, creds.tan_medium
            )

            # Build HKTAN segment for dialog init
            # NOTE: tan_medium_name must be None (not the actual TAN medium!)
            # This matches legacy client behavior exactly.
            hktan = self._build_hktan_for_init(parameters)
            if hktan:
                extra_init_segments.append(hktan)

        # Create security mechanisms
        # IMPORTANT: HNVSK (encryption) uses security_method_version=2 for two-step TAN
        # while HNSHK (signature) uses security_method_version=1
        # This matches legacy client behavior exactly!
        enc_version = 2 if creds.tan_method else 1
        enc_mechanism = StandaloneEncryptionMechanism(
            security_context,
            security_method_version=enc_version,
        )
        auth_mechanism = StandaloneAuthenticationMechanism(
            context=security_context,
            pin=str(creds.pin),  # Convert Password to str
            security_function=security_function,
        )

        # Create dialog with security function for two-step TAN support
        dialog = Dialog(
            connection=connection,
            config=dialog_config,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=[auth_mechanism],
            security_function=security_function,
        )

        return dialog, extra_init_segments

    def _build_hktan_for_init(
        self,
        parameters: ParameterStore,
    ) -> Any:
        """
        Build HKTAN segment for dialog initialization (tan_process='4').

        Uses BPD to determine the HKTAN version supported by the bank.
        The legacy client sends HKTAN with:
        - tan_process='4'
        - segment_type='HKIDN' (for version >= 6)
        - tan_medium_name=None (NOT the actual TAN medium!)

        Returns:
            HKTAN segment or None if not supported
        """
        # Find highest version HITANS in BPD to determine supported HKTAN version
        hitans = None
        for seg in parameters.bpd.segments.find_segments("HITANS"):
            if hitans is None or seg.header.version > hitans.header.version:
                hitans = seg

        if not hitans:
            logger.warning("No HITANS in BPD, cannot build HKTAN")
            return None

        # Get HKTAN version from HITANS version (use highest available)
        hktan_version = hitans.header.version
        hktan_class = HKTAN_VERSIONS.get(hktan_version)
        if not hktan_class:
            logger.warning("HKTAN version %d not directly supported, trying lower", hktan_version)
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

        # For HKTAN >= 6, set segment_type to HKIDN (the init segment type)
        if hktan_version >= 6 and hasattr(seg, "segment_type"):
            seg.segment_type = "HKIDN"

        # IMPORTANT: Do NOT set tan_medium_name!
        # The legacy client sends it as None, and setting it causes
        # bank error 9110 "Falsche Segmentzusammenstellung"

        return seg

    def _ensure_system_id(
        self,
        connection: HTTPSDialogConnection,
        bank_id: BankIdentifier,
        parameters: ParameterStore,
        creds: GatewayCredentials,
    ) -> str:
        """
        Obtain a system ID from the bank via HKSYN3/HISYN4.

        This opens a separate dialog using one-step auth (security function 999)
        to get the system ID and initial BPD. The BPD is needed to know which
        TAN mechanisms the bank supports.

        Args:
            connection: HTTP connection to reuse
            bank_id: Bank identifier
            parameters: Parameter store to update with BPD
            creds: Credentials

        Returns:
            System ID from the bank
        """
        logger.info("No system ID, requesting from bank via sync dialog...")

        # Build dialog config without system ID
        dialog_config = DialogConfig(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            customer_id=creds.customer_id or creds.user_id,
            system_id=SYSTEM_ID_UNASSIGNED,
            product_name=creds.product_id,
            product_version=creds.product_version,
        )

        # Create security context
        security_context = SecurityContext(
            bank_identifier=bank_id,
            user_id=creds.user_id,
            system_id=SYSTEM_ID_UNASSIGNED,
        )

        # For sync dialog, always use one-step auth (security_function=999)
        # Some banks (like DKB) reject two-step TAN during sync/identification
        # The actual TAN method is only used in the main dialog
        security_function = "999"
        enc_mechanism = StandaloneEncryptionMechanism(
            security_context, security_method_version=1  # One-step for sync
        )
        auth_mechanism = StandaloneAuthenticationMechanism(
            context=security_context,
            pin=str(creds.pin),
            security_function=security_function,
        )

        # Create sync dialog (no HKTAN injection needed for HKSYN)
        sync_dialog = Dialog(
            connection=connection,
            config=dialog_config,
            parameters=parameters,
            enc_mechanism=enc_mechanism,
            auth_mechanisms=[auth_mechanism],
            security_function=security_function,  # Pass for consistency
        )

        try:
            # Initialize with HKSYN3 to request system ID
            response = sync_dialog.initialize(
                extra_segments=[HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)]
            )

            # Extract system ID from HISYN4 response
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
            # Close sync dialog
            if sync_dialog.is_open:
                try:
                    sync_dialog.end()
                except Exception:
                    logger.exception("Error closing sync dialog")

    def _build_parameters(
        self,
        state: FinTSSessionState | None,
    ) -> ParameterStore:
        """Build parameter store from state or create empty."""
        if state and state.client_blob:
            try:
                data = self._extract_params_dict(state.client_blob)
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
        self,
        client_blob: bytes | Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        """Extract parameter dictionary from client blob.

        The client blob can be:
        1. Compressed bytes (legacy format, for session state migration)
        2. A plain dictionary (from ParameterStore.to_dict())

        Args:
            client_blob: Either compressed bytes or a dictionary

        Returns:
            Dictionary suitable for ParameterStore.from_dict()
        """
        if isinstance(client_blob, dict):
            # Already a dictionary (new format)
            return client_blob

        if isinstance(client_blob, bytes):
            # Legacy compressed format
            try:
                # decompress_datablob returns (version, data) when no object provided
                _version, data = decompress_datablob(DATA_BLOB_MAGIC, client_blob)
                return data
            except (ValueError, Exception) as e:
                logger.debug("Failed to decompress blob: %s", e)
                return None

        return None

    def create_session_state(
        self,
        ctx: ConnectionContext,
    ) -> FinTSSessionState:
        """
        Create session state from active connection context.

        Args:
            ctx: Active connection context

        Returns:
            FinTSSessionState for persistence
        """
        # Store in compressed format for compatibility with legacy client
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


__all__ = ["ConnectionContext", "FinTSConnectionHelper"]
