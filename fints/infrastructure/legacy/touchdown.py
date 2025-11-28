"""Pagination helpers for touchdown-based FinTS queries."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

from fints.message import FinTSInstituteMessage

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from fints.client import FinTS3Client
    from fints.dialog import FinTSDialog
    from fints.segments.base import FinTS3Segment


logger = logging.getLogger(__name__)


class TouchdownPaginator:
    """Handles FinTS touchdown paging loops for a given client."""

    def __init__(self, owner: "FinTS3Client") -> None:
        self._owner = owner

    def fetch(
        self,
        dialog: "FinTSDialog",
        segment_factory: Callable[[Optional[str]], "FinTS3Segment"],
        response_processor: Callable[[list[Any]], Any],
        *response_args,
        **response_kwargs,
    ) -> Any:
        """Run a touchdown-enabled query until the bank stops returning pointer 3040."""

        responses: list[Any] = []
        counter = 1

        def _resume(command_seg, response: FinTSInstituteMessage):
            nonlocal counter
            for resp in response.response_segments(
                command_seg,
                *response_args,
                **response_kwargs,
            ):
                responses.append(resp)

            touchdown = None
            for resp in response.responses(command_seg, '3040'):
                touchdown = resp.parameters[0]
                break

            if touchdown:
                logger.info('Fetching more results (%s)...', counter)
                counter += 1
                next_seg = segment_factory(touchdown)
                return self._owner._send_with_possible_retry(dialog, next_seg, _resume)

            return response_processor(responses)

        first_seg = segment_factory(None)
        return self._owner._send_with_possible_retry(dialog, first_seg, _resume)
