"""TAN media discovery for FinTS PIN/TAN."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from fints.formals import TANMediaClass4, TANMediaType2, TANUsageOption

if TYPE_CHECKING:
    pass


@dataclass
class TanMediaInfo:
    """Information about a TAN medium (device, app, list)."""

    name: str
    media_class: str
    status: str
    phone_number: str | None = None
    card_number: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    tan_list_number: str | None = None


class TanMediaDiscovery:
    """
    Discovers available TAN media for a user.

    TAN media are the devices or mechanisms used to generate or
    receive TANs (e.g., smartphone apps, TAN generators, SMS).
    """

    def __init__(self, bpd_segments, dialog_send_func) -> None:
        """
        Initialize TAN media discovery.

        Args:
            bpd_segments: Bank parameter data segments
            dialog_send_func: Function to send segments in dialog
        """
        self._bpd = bpd_segments
        self._send = dialog_send_func

    def get_available_media(
        self,
        media_type: TANMediaType2 = TANMediaType2.ALL,
        media_class: TANMediaClass4 = TANMediaClass4.ALL,
    ) -> tuple[TANUsageOption, Sequence[TanMediaInfo]]:
        """
        Query available TAN media from the bank.

        Args:
            media_type: Filter by media type
            media_class: Filter by media class

        Returns:
            Tuple of (usage_option, list of TanMediaInfo)
        """
        from fints.segments.auth import HKTAB4, HKTAB5

        # Find highest supported HKTAB version
        hktab = self._find_hktab_command()
        if not hktab:
            return TANUsageOption.ALL_ACTIVE, []

        # Build and send request
        if hktab == HKTAB5:
            seg = hktab(
                tan_media_type=media_type,
                tan_media_class=str(media_class),
            )
        else:
            seg = hktab(
                tan_media_type=media_type,
                tan_media_class=str(media_class),
            )

        response = self._send(seg)

        # Parse response
        for resp in response.response_segments(seg, "HITAB"):
            media_list = self._parse_media_list(resp.tan_media_list or [])
            return resp.tan_usage_option, media_list

        return TANUsageOption.ALL_ACTIVE, []

    def _find_hktab_command(self):
        """Find the highest supported HKTAB version."""
        from fints.segments.auth import HKTAB4, HKTAB5

        # Check for HITABS parameter segment
        for version, cls in [(5, HKTAB5), (4, HKTAB4)]:
            param_type = f"HITABS{version}"
            if self._bpd.find_segment(param_type):
                return cls
        return None

    def _parse_media_list(self, raw_list) -> Sequence[TanMediaInfo]:
        """Parse TAN media list from response."""
        media = []
        for item in raw_list:
            info = TanMediaInfo(
                name=getattr(item, "tan_medium_name", "") or "",
                media_class=str(getattr(item, "tan_medium_class", "")),
                status=str(getattr(item, "status", "")),
                phone_number=getattr(item, "mobile_phone_number", None),
                card_number=getattr(item, "card_number", None),
                valid_from=str(getattr(item, "valid_from", "")) or None,
                valid_until=str(getattr(item, "valid_until", "")) or None,
                tan_list_number=getattr(item, "tan_list_number", None),
            )
            media.append(info)
        return media


__all__ = [
    "TanMediaDiscovery",
    "TanMediaInfo",
]

