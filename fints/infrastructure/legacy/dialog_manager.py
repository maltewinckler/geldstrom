"""Session management helpers for the legacy FinTS client."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from fints.dialog import FinTSDialog
from fints.exceptions import FinTSSCARequiredError

if TYPE_CHECKING:  # pragma: no cover - import guard for typing only
    from fints.client import FinTS3Client


class DialogSessionManager:
    """Coordinates the lifetime of FinTS dialog sessions for a client."""

    def __init__(self, owner: "FinTS3Client") -> None:
        self._owner = owner
        self._standing_dialog = None

    # ------------------------------------------------------------------
    # Exposed compatibility accessors
    # ------------------------------------------------------------------

    @property
    def standing_dialog(self):
        return self._standing_dialog

    @standing_dialog.setter
    def standing_dialog(self, dialog) -> None:
        self._standing_dialog = dialog

    # ------------------------------------------------------------------

    def enter(self) -> None:
        """Start a standing dialog context for the owner client."""
        if self._standing_dialog:
            raise Exception(f"Cannot double __enter__() {self._owner}")
        dialog = self.get_dialog()
        self._standing_dialog = dialog
        dialog.__enter__()

    def exit(self, exc_type, exc, tb) -> None:
        """Close the standing dialog context."""
        if not self._standing_dialog:
            raise Exception(f"Cannot double __exit__() {self._owner}")
        if exc_type is not None and issubclass(exc_type, FinTSSCARequiredError):
            # Bank already closed the dialog in case of SCA errors.
            self._standing_dialog.open = False
        else:
            self._standing_dialog.__exit__(exc_type, exc, tb)
        self._standing_dialog = None

    def get_dialog(self, lazy_init: bool = False):
        """Return an active dialog, optionally reusing the standing context."""
        if lazy_init and self._standing_dialog:
            raise Exception("Cannot _get_dialog(lazy_init=True) with _standing_dialog")
        if self._standing_dialog:
            return self._standing_dialog
        if not lazy_init:
            self._owner._ensure_system_id()
        return self._owner._new_dialog(lazy_init=lazy_init)

    def pause(self):
        """Pause the current standing dialog and return its serialized state."""
        if not self._standing_dialog:
            raise Exception("Cannot pause dialog, no standing dialog exists")
        return self._standing_dialog.pause()

    @contextmanager
    def resume(self, dialog_data):
        """Resume a previously paused dialog for the duration of a context manager."""
        if self._standing_dialog:
            raise Exception("Cannot resume dialog, existing standing dialog")
        self._standing_dialog = FinTSDialog.create_resume(self._owner, dialog_data)
        with self._standing_dialog:
            yield self._owner
        self._standing_dialog = None
