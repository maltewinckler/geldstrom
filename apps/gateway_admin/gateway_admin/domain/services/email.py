"""Email service abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmailService(ABC):
    @abstractmethod
    async def send_token_email(self, recipient_email: str, token: str) -> None: ...
