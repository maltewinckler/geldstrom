"""System ID synchronization for FinTS dialogs.

This module handles the HKSYN3/HISYN4 segment exchange required to obtain
a unique system ID from the bank. System IDs are required for non-anonymous
users and are persisted across sessions.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from geldstrom.constants import SYSTEM_ID_UNASSIGNED
from geldstrom.infrastructure.fints.protocol import (
    CUSTOMER_ID_ANONYMOUS,
    HKSYN3,
    HISYN4,
    SynchronizationMode,
)

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog, DialogFactory
    from geldstrom.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)


class SystemIdSynchronizer:
    """
    Handles system ID synchronization with the bank.

    A system ID uniquely identifies this client installation to the bank.
    It's required for non-anonymous users and should be persisted for reuse.

    Usage:
        synchronizer = SystemIdSynchronizer(dialog_factory, parameters)
        system_id = synchronizer.ensure_system_id(
            current_system_id=SYSTEM_ID_UNASSIGNED,
            customer_id="user123",
        )
    """

    def __init__(
        self,
        dialog_factory: "DialogFactory",
        parameters: "ParameterStore",
    ) -> None:
        """
        Initialize the synchronizer.

        Args:
            dialog_factory: Factory to create dialogs for sync
            parameters: Parameter store for BPD/UPD updates
        """
        self._dialog_factory = dialog_factory
        self._parameters = parameters

    def ensure_system_id(
        self,
        current_system_id: str,
        customer_id: str,
    ) -> str:
        """
        Ensure we have a valid system ID, obtaining one if needed.

        Args:
            current_system_id: Current system ID (may be unassigned)
            customer_id: Customer ID for the session

        Returns:
            Valid system ID (either existing or newly obtained)

        Raises:
            ValueError: If system ID cannot be obtained from bank
        """
        # Check if we already have a valid system ID
        if current_system_id != SYSTEM_ID_UNASSIGNED:
            logger.debug("Using existing system ID: %s", current_system_id)
            return current_system_id

        # Anonymous users don't need system IDs
        if customer_id == CUSTOMER_ID_ANONYMOUS:
            logger.debug("Anonymous user, no system ID needed")
            return SYSTEM_ID_UNASSIGNED

        # Need to request a new system ID from the bank
        logger.info("Requesting new system ID from bank")
        return self._request_new_system_id()

    def _request_new_system_id(self) -> str:
        """
        Request a new system ID from the bank via HKSYN3/HISYN4.

        Returns:
            Newly assigned system ID

        Raises:
            ValueError: If bank doesn't return a system ID
        """
        # Open a dialog with lazy_init to include HKSYN3 in init
        with self._dialog_factory.open_dialog(
            lazy_init=True,
            extra_init_segments=[HKSYN3(synchronization_mode=SynchronizationMode.NEW_SYSTEM_ID)],
        ) as dialog:
            # Initialize with sync request
            response = dialog.initialize()

            # Find HISYN4 response with system ID
            seg = response.find_segment_first(HISYN4)
            if not seg:
                raise ValueError(
                    "Could not obtain system ID from bank - HISYN4 segment not found"
                )

            system_id = seg.system_id
            logger.info("Obtained new system ID: %s", system_id)
            return system_id


def ensure_system_id(
    dialog_factory: "DialogFactory",
    parameters: "ParameterStore",
    current_system_id: str,
    customer_id: str,
) -> str:
    """
    Convenience function to ensure system ID.

    Args:
        dialog_factory: Factory to create dialogs
        parameters: Parameter store
        current_system_id: Current system ID
        customer_id: Customer ID

    Returns:
        Valid system ID
    """
    synchronizer = SystemIdSynchronizer(dialog_factory, parameters)
    return synchronizer.ensure_system_id(current_system_id, customer_id)

