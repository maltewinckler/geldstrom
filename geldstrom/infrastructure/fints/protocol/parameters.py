"""Bank and user parameter data management for FinTS dialogs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .base import SegmentSequence
from .parser import FinTSSerializer

logger = logging.getLogger(__name__)


@dataclass
class BankParameters:
    """
    Bank Parameter Data (BPD) from FinTS dialog.

    BPD contains information about the bank's capabilities, supported
    operations, and protocol parameters. It is updated during dialog
    initialization when the bank provides new BPD.
    """

    version: int = 0
    bank_name: str | None = None
    segments: SegmentSequence = field(default_factory=SegmentSequence)
    bpa: Any = None  # HIBPA segment

    def find_segment(self, segment_type: str, version: int | None = None) -> Any:
        """
        Find a segment in BPD by type and optionally version.

        Args:
            segment_type: Segment type code (e.g., 'HISALS')
            version: Optional specific version to match

        Returns:
            The matching segment or None
        """
        for seg in self.segments.find_segments(segment_type):
            if version is None or seg.header.version == version:
                return seg
        return None

    def find_segment_highest_version(
        self, segment_type: str, supported_versions: Iterable[int]
    ) -> Any:
        """
        Find the highest version of a segment supported by both bank and client.

        Args:
            segment_type: Segment type code
            supported_versions: Versions the client supports

        Returns:
            The matching segment with highest version, or None
        """
        return self.segments.find_segment_highest_version(
            segment_type, supported_versions
        )

    def supports_operation(self, segment_type: str) -> bool:
        """
        Check if the bank supports a specific operation.

        Args:
            segment_type: The HKXXX segment type

        Returns:
            True if the bank's BPD indicates support
        """
        # Convert HKXXX to HIXXX+S parameter segment
        if segment_type.startswith("HK"):
            param_type = f"HI{segment_type[2:]}S"
            return self.find_segment(param_type) is not None
        return False

    def get_supported_operations(self) -> Mapping[str, bool]:
        """
        Return a mapping of operation types to their support status.

        Returns:
            Dict mapping segment types to boolean support status
        """
        from geldstrom.infrastructure.fints import FinTSOperations

        return {
            op.name: any(
                self.find_segment(f"{cmd[0]}I{cmd[2:]}S") is not None
                for cmd in op.value
            )
            for op in FinTSOperations
        }

    def serialize(self) -> bytes:
        """Serialize BPD for storage."""
        return self.segments.render_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, bpa_data: bytes | None = None) -> "BankParameters":
        """
        Restore BPD from serialized bytes.

        Args:
            data: Serialized BPD segment data
            bpa_data: Optional serialized BPA segment

        Returns:
            Restored BankParameters instance
        """
        # Handle empty/invalid segment data
        # Empty SegmentSequence renders as b"'" which is not valid
        segments = SegmentSequence()
        if data and len(data) > 1:  # Need at least 2 bytes for valid segment
            try:
                segments = SegmentSequence(data)
            except Exception:
                logger.debug("Failed to parse BPD segments from %d bytes", len(data))

        bpa = None
        if bpa_data and len(bpa_data) > 1:
            try:
                bpa_segments = SegmentSequence(bpa_data)
                if bpa_segments.segments:
                    bpa = bpa_segments.segments[0]
            except Exception:
                logger.debug("Failed to parse BPA segment")

        version = bpa.bpd_version if bpa else 0
        bank_name = bpa.bank_name if bpa and hasattr(bpa, "bank_name") else None

        return cls(
            version=version,
            bank_name=bank_name,
            segments=segments,
            bpa=bpa,
        )


@dataclass
class UserParameters:
    """
    User Parameter Data (UPD) from FinTS dialog.

    UPD contains information about the user's accounts and their
    associated permissions. It is updated when the bank provides new UPD.
    """

    version: int = 0
    segments: SegmentSequence = field(default_factory=SegmentSequence)
    upa: Any = None  # HIUPA segment

    def get_accounts(self) -> Sequence[Mapping[str, Any]]:
        """
        Extract account information from UPD.

        Returns:
            List of account dictionaries with relevant fields
        """
        accounts = []
        count_segments = 0
        for upd in self.segments.find_segments("HIUPD"):
            count_segments += 1
            # account_information may be None for some banks (e.g., DKB)
            acc_info = getattr(upd, "account_information", None)
            acc = {
                "iban": getattr(upd, "iban", None),
                "account_number": (
                    acc_info.account_number if acc_info else None
                ),
                "subaccount_number": (
                    acc_info.subaccount_number if acc_info else None
                ),
                "bank_identifier": (
                    acc_info.bank_identifier if acc_info else None
                ),
                "customer_id": getattr(upd, "customer_id", None),
                "type": getattr(upd, "account_type", None),
                "currency": getattr(upd, "account_currency", None),
                "owner_name": [],
                "product_name": getattr(upd, "account_product_name", None),
                "allowed_transactions": getattr(
                    upd, "allowed_transactions", []
                ),
            }
            owner_1 = getattr(upd, "name_account_owner_1", None)
            owner_2 = getattr(upd, "name_account_owner_2", None)
            if owner_1:
                acc["owner_name"].append(owner_1)
            if owner_2:
                acc["owner_name"].append(owner_2)
            accounts.append(acc)
        logger.warning("UserParameters.get_accounts found %d HIUPD segments", count_segments)
        return accounts

    def get_account_capabilities(
        self, account_number: str, subaccount: str | None = None
    ) -> Mapping[str, bool]:
        """
        Get capabilities for a specific account.

        Args:
            account_number: Account number
            subaccount: Optional subaccount number

        Returns:
            Dict mapping operation names to boolean support
        """
        from geldstrom.infrastructure.fints import FinTSOperations

        for upd in self.segments.find_segments("HIUPD"):
            if upd.account_information.account_number != account_number:
                continue
            if subaccount and upd.account_information.subaccount_number != subaccount:
                continue

            return {
                op.name: any(
                    allowed.transaction in op.value
                    for allowed in upd.allowed_transactions
                )
                for op in FinTSOperations
            }
        return {}

    def serialize(self) -> bytes:
        """Serialize UPD for storage."""
        return self.segments.render_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, upa_data: bytes | None = None) -> "UserParameters":
        """
        Restore UPD from serialized bytes.

        Args:
            data: Serialized UPD segment data
            upa_data: Optional serialized UPA segment

        Returns:
            Restored UserParameters instance
        """
        # Handle empty/invalid segment data
        # Empty SegmentSequence renders as b"'" which is not valid
        segments = SegmentSequence()
        if data and len(data) > 1:  # Need at least 2 bytes for valid segment
            try:
                segments = SegmentSequence(data)
            except Exception:
                logger.debug("Failed to parse UPD segments from %d bytes", len(data))

        upa = None
        if upa_data and len(upa_data) > 1:
            try:
                upa_segments = SegmentSequence(upa_data)
                if upa_segments.segments:
                    upa = upa_segments.segments[0]
            except Exception:
                logger.debug("Failed to parse UPA segment")

        version = upa.upd_version if upa else 0

        return cls(version=version, segments=segments, upa=upa)


class ParameterStore:
    """
    Manages bank and user parameters for a FinTS session.

    This class handles:
    - Storing and updating BPD/UPD from dialog responses
    - Caching parameters for session reuse
    - Serialization/deserialization for persistence
    """

    def __init__(
        self,
        bpd: BankParameters | None = None,
        upd: UserParameters | None = None,
    ) -> None:
        """
        Initialize parameter store.

        Args:
            bpd: Optional initial bank parameters
            upd: Optional initial user parameters
        """
        self._bpd = bpd or BankParameters()
        self._upd = upd or UserParameters()

    @property
    def bpd(self) -> BankParameters:
        """Return bank parameter data."""
        return self._bpd

    @property
    def upd(self) -> UserParameters:
        """Return user parameter data."""
        return self._upd

    @property
    def bpd_version(self) -> int:
        """Return current BPD version."""
        return self._bpd.version

    @property
    def upd_version(self) -> int:
        """Return current UPD version."""
        return self._upd.version

    def update_from_response(
        self,
        bpa: Any | None,
        bpd_version: int | None,
        bpd_segments: SegmentSequence | None,
        upa: Any | None,
        upd_version: int | None,
        upd_segments: SegmentSequence | None,
    ) -> None:
        """
        Update parameters from a processed dialog response.

        Only updates if the new version is higher than current.

        Args:
            bpa: Bank parameter administration segment
            bpd_version: New BPD version
            bpd_segments: New BPD segments
            upa: User parameter administration segment
            upd_version: New UPD version
            upd_segments: New UPD segments
        """
        # Update BPD if newer
        if bpd_version is not None and bpd_version >= self._bpd.version and bpd_segments:
            bank_name = bpa.bank_name if bpa and hasattr(bpa, "bank_name") else None
            self._bpd = BankParameters(
                version=bpd_version,
                bank_name=bank_name,
                segments=bpd_segments,
                bpa=bpa,
            )
            logger.debug("Updated BPD to version %d", bpd_version)

        # Update UPD if newer
        if upd_version is not None and upd_version >= self._upd.version and upd_segments:
            logger.warning(
                "Updating UPD to version %d with %d segments",
                upd_version,
                len(upd_segments.segments),
            )
            self._upd = UserParameters(
                version=upd_version,
                segments=upd_segments,
                upa=upa,
            )
            logger.debug("Updated UPD to version %d", upd_version)

    def to_dict(self) -> Mapping[str, Any]:
        """Serialize parameter store to a dictionary.

        Handles both Pydantic and legacy segments.
        """
        def serialize_segment(segment):
            """Serialize a single segment using the Pydantic serializer."""
            if segment is None:
                return None
            serializer = FinTSSerializer()
            return serializer.serialize_message(segment)

        return {
            "bpd_version": self._bpd.version,
            "bpd_bin": self._bpd.serialize(),
            "bpa_bin": serialize_segment(self._bpd.bpa),
            "upd_version": self._upd.version,
            "upd_bin": self._upd.serialize(),
            "upa_bin": serialize_segment(self._upd.upa),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ParameterStore":
        """Restore parameter store from a dictionary."""
        bpd = BankParameters.from_bytes(
            data.get("bpd_bin", b""),
            data.get("bpa_bin"),
        )
        bpd.version = data.get("bpd_version", 0)

        upd = UserParameters.from_bytes(
            data.get("upd_bin", b""),
            data.get("upa_bin"),
        )
        upd.version = data.get("upd_version", 0)

        return cls(bpd=bpd, upd=upd)

