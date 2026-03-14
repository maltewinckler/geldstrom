"""Stateless domain services for bank-facing operations."""

from __future__ import annotations

from gateway.domain.shared import DomainError

from .value_objects import PresentedBankCredentials


class BankRequestSanitizationPolicy:
    """Guardrails for transient secret-bearing bank requests."""

    @staticmethod
    def sanitize(credentials: PresentedBankCredentials) -> None:
        user_id = credentials.user_id.value.get_secret_value().strip()
        password = credentials.password.value.get_secret_value().strip()
        if not user_id:
            raise DomainError("Presented bank user id must not be empty")
        if not password:
            raise DomainError("Presented bank password must not be empty")
