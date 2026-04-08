"""Bank and user parameter data management for FinTS dialogs."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .base import SegmentSequence
from .parser import FinTSSerializer

logger = logging.getLogger(__name__)


@dataclass
class BankParameters:
    """Bank Parameter Data (BPD) from a FinTS dialog."""

    version: int = 0
    bank_name: str | None = None
    segments: SegmentSequence = field(default_factory=SegmentSequence)
    bpa: Any = None  # HIBPA segment

    def find_segment(self, segment_type: str) -> Any:
        return self.segments.find_segment_first(segment_type)

    def get_supported_operations(self) -> Mapping[str, bool]:
        from geldstrom.infrastructure.fints.operations import FinTSOperations

        return {
            op.name: self.find_segment(f"HI{op.value[2:]}S") is not None
            for op in FinTSOperations
        }

    def serialize(self) -> bytes:
        """Serialize BPD for storage."""
        return self.segments.render_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, bpa_data: bytes | None = None) -> BankParameters:
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
    """User Parameter Data (UPD) from a FinTS dialog."""

    version: int = 0
    segments: SegmentSequence = field(default_factory=SegmentSequence)
    upa: Any = None  # HIUPA segment

    def get_accounts(self) -> Sequence[Mapping[str, Any]]:
        accounts = []
        count_segments = 0
        for upd in self.segments.find_segments("HIUPD"):
            count_segments += 1
            # account_information may be None for some banks (e.g., DKB)
            acc_info = getattr(upd, "account_information", None)
            acc = {
                "iban": getattr(upd, "iban", None),
                "account_number": (acc_info.account_number if acc_info else None),
                "subaccount_number": (acc_info.subaccount_number if acc_info else None),
                "bank_identifier": (acc_info.bank_identifier if acc_info else None),
                "customer_id": getattr(upd, "customer_id", None),
                "type": getattr(upd, "account_type", None),
                "currency": getattr(upd, "account_currency", None),
                "owner_name": [],
                "product_name": getattr(upd, "account_product_name", None),
                "allowed_transactions": getattr(upd, "allowed_transactions", []),
            }
            owner_1 = getattr(upd, "name_account_owner_1", None)
            owner_2 = getattr(upd, "name_account_owner_2", None)
            if owner_1:
                acc["owner_name"].append(owner_1)
            if owner_2:
                acc["owner_name"].append(owner_2)
            accounts.append(acc)
        logger.debug(
            "UserParameters.get_accounts found %d HIUPD segments", count_segments
        )
        return accounts

    def serialize(self) -> bytes:
        """Serialize UPD for storage."""
        return self.segments.render_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, upa_data: bytes | None = None) -> UserParameters:
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
    """Manages BPD and UPD for a FinTS session (with update, serialize, restore)."""

    def __init__(
        self,
        bpd: BankParameters | None = None,
        upd: UserParameters | None = None,
    ) -> None:
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
        """Update BPD/UPD from a dialog response if the new version is higher."""
        if (
            bpd_version is not None
            and bpd_version >= self._bpd.version
            and bpd_segments is not None
        ):
            bank_name = bpa.bank_name if bpa and hasattr(bpa, "bank_name") else None
            self._bpd = BankParameters(
                version=bpd_version,
                bank_name=bank_name,
                segments=bpd_segments,
                bpa=bpa,
            )
            logger.debug("Updated BPD to version %d", bpd_version)

        if (
            upd_version is not None
            and upd_version >= self._upd.version
            and upd_segments is not None
        ):
            logger.debug(
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
        """Serialize parameter store to a dictionary."""
        serializer = FinTSSerializer()

        def serialize_segment(segment: Any) -> bytes | None:
            if segment is None:
                return None
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
    def from_dict(cls, data: Mapping[str, Any]) -> ParameterStore:
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
