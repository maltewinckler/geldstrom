"""SMTP email service - implements EmailService port."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from gateway_admin.domain.services.email import EmailService

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str


class SmtpEmailService(EmailService):
    """SMTP-based email service."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._from_email = from_email
        self._use_tls = use_tls

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        s = repo_factory.settings
        return cls(
            smtp_host=s.smtp_host,
            smtp_port=s.smtp_port,
            smtp_user=s.smtp_user,
            smtp_password=s.smtp_password.get_secret_value(),
            from_email=s.smtp_from_email,
            use_tls=s.smtp_use_tls,
        )

    async def send_token_email(self, recipient_email: str, token: str) -> None:
        await self._send(
            EmailMessage(
                to=recipient_email,
                subject="Your Gateway API Credentials",
                body=token,
            )
        )

    async def _send(self, message: EmailMessage) -> None:
        from email.message import EmailMessage as StdEmailMessage

        import aiosmtplib

        email = StdEmailMessage()
        email["From"] = self._from_email
        email["To"] = message.to
        email["Subject"] = message.subject
        email.set_content(message.body)

        try:
            await aiosmtplib.send(
                email,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._smtp_user,
                password=self._smtp_password,
                use_tls=self._use_tls,
            )
        except aiosmtplib.SMTPAuthenticationError as e:
            raise EmailAuthenticationError(
                f"SMTP authentication failed for {self._smtp_user}@{self._smtp_host}: {e}"
            ) from e
        except aiosmtplib.SMTPException as e:
            raise EmailSendError(
                f"Failed to send email via {self._smtp_host}:{self._smtp_port}: {e}"
            ) from e
        except OSError as e:
            raise EmailConnectionError(
                f"Cannot connect to SMTP server {self._smtp_host}:{self._smtp_port}: {e}"
            ) from e


class MockEmailService(EmailService):
    """In-memory email service for testing."""

    def __init__(self) -> None:
        self._sent_emails: list[EmailMessage] = []

    async def send_token_email(self, recipient_email: str, token: str) -> None:
        self._sent_emails.append(
            EmailMessage(
                to=recipient_email,
                subject="Your Gateway API Credentials",
                body=token,
            )
        )

    @property
    def sent_emails(self) -> list[EmailMessage]:
        return self._sent_emails.copy()

    def clear(self) -> None:
        self._sent_emails.clear()


# Email-specific exceptions
class EmailServiceError(Exception):
    pass


class EmailConnectionError(EmailServiceError):
    pass


class EmailAuthenticationError(EmailServiceError):
    pass


class EmailSendError(EmailServiceError):
    pass
