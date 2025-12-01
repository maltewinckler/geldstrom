"""HTTP/HTTPS connection handling for FinTS dialogs."""
from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass, field
from typing import Protocol

import requests

from geldstrom.exceptions import FinTSConnectionError
from geldstrom.message import FinTSInstituteMessage, FinTSMessage
from geldstrom.infrastructure.fints.protocol.base import SegmentSequence
from geldstrom.utils import Password, log_configuration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectionConfig:
    """Configuration for FinTS connection parameters."""

    url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str | None = None


class DialogConnection(Protocol):
    """Protocol for FinTS dialog transport connections."""

    def send_raw(self, data: bytes) -> bytes:
        """
        Send raw bytes and receive raw response.

        Args:
            data: Raw message bytes to send

        Returns:
            Raw response bytes from the server

        Raises:
            FinTSConnectionError: If the connection fails
        """
        ...

    def close(self) -> None:
        """Close the connection and release resources."""
        ...


def _reduce_message_for_log(msg: FinTSMessage) -> FinTSMessage | SegmentSequence:
    """Reduce message content for logging when configured."""
    log_msg = msg
    if log_configuration.reduced:
        # Try to find a single inner message
        if (
            len(log_msg.segments) == 4
            and log_msg.segments[2].header.type == "HNVSD"
        ):
            log_msg = log_msg.segments[2]
            if (
                len(log_msg.data.segments) > 2
                and log_msg.data.segments[0].header.type == "HNSHK"
                and log_msg.data.segments[-1].header.type == "HNSHA"
            ):
                log_msg = SegmentSequence(segments=log_msg.data.segments[1:-1])
    return log_msg


class HTTPSDialogConnection:
    """HTTPS implementation of DialogConnection for FinTS 3.0."""

    def __init__(self, config: ConnectionConfig | str) -> None:
        """
        Initialize HTTPS connection.

        Args:
            config: ConnectionConfig or URL string for simple initialization
        """
        if isinstance(config, str):
            config = ConnectionConfig(url=config)
        self._config = config
        self._session = requests.Session()
        if config.user_agent:
            self._session.headers["User-Agent"] = config.user_agent

    @property
    def url(self) -> str:
        """Return the connection URL."""
        return self._config.url

    def send_raw(self, data: bytes) -> bytes:
        """
        Send raw bytes and receive raw response.

        The data is base64 encoded before sending and the response
        is base64 decoded, per FinTS 3.0 HTTPS transport specification.

        Args:
            data: Raw message bytes to send

        Returns:
            Raw response bytes from the server

        Raises:
            FinTSConnectionError: If the connection fails
        """
        try:
            response = self._session.post(
                self._config.url,
                data=base64.b64encode(data),
                headers={"Content-Type": "text/plain"},
                timeout=self._config.timeout,
            )
        except requests.RequestException as e:
            raise FinTSConnectionError(f"Connection failed: {e}") from e

        if response.status_code < 200 or response.status_code > 299:
            raise FinTSConnectionError(f"Bad status code {response.status_code}")

        return base64.b64decode(response.content.decode("iso-8859-1"))

    def send(self, msg: FinTSMessage) -> FinTSInstituteMessage:
        """
        Send a FinTS message and receive the institute response.

        This is a higher-level method that handles logging and
        parsing of the response into a FinTSInstituteMessage.

        Args:
            msg: FinTS message to send

        Returns:
            Parsed institute response message
        """
        # Log outgoing message
        log_out = io.StringIO()
        with Password.protect():
            log_msg = _reduce_message_for_log(msg)
            log_msg.print_nested(stream=log_out, prefix="\t")
            abbrev = "(abbrv.)" if log_configuration.reduced else ""
            logger.debug(
                "Sending %s>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n%s\n"
                ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n",
                abbrev,
                log_out.getvalue(),
            )
            log_out.truncate(0)

        # Send and receive
        response_bytes = self.send_raw(msg.render_bytes())
        retval = FinTSInstituteMessage(segments=response_bytes)

        # Log incoming message
        with Password.protect():
            log_msg = _reduce_message_for_log(retval)
            log_msg.print_nested(stream=log_out, prefix="\t")
            abbrev = "(abbrv.)" if log_configuration.reduced else ""
            logger.debug(
                "Received %s<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n%s\n"
                "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n",
                abbrev,
                log_out.getvalue(),
            )

        return retval

    def close(self) -> None:
        """Close the session and release resources."""
        self._session.close()

    def __enter__(self) -> "HTTPSDialogConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# Keep backward compatibility with the original class name
FinTSHTTPSConnection = HTTPSDialogConnection

