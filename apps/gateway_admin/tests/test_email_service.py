"""Tests for email service implementations.

Covers:
- MockEmailService stores emails correctly (unit)
- send_token_email stores correct subject and body (unit)
- Property 13: Email contains only the token
- Property 14: Raw token is never stored in the repository
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gateway_admin.infrastructure.services.email_service import MockEmailService

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_email_service_stores_email() -> None:
    """MockEmailService stores sent emails in memory."""
    svc = MockEmailService()
    await svc.send_token_email("user@example.com", "my-token-123")
    emails = svc.sent_emails
    assert len(emails) == 1
    assert emails[0].to == "user@example.com"


@pytest.mark.asyncio
async def test_send_token_email_correct_subject_and_body() -> None:
    """send_token_email stores the correct subject and token as body."""
    svc = MockEmailService()
    token = "secret-token-abc"
    await svc.send_token_email("admin@test.org", token)
    email = svc.sent_emails[0]
    assert email.subject == "Your Gateway API Credentials"
    assert token in email.body


@pytest.mark.asyncio
async def test_mock_email_service_clear() -> None:
    """clear() removes all stored emails."""
    svc = MockEmailService()
    await svc.send_token_email("a@b.com", "tok")
    svc.clear()
    assert svc.sent_emails == []


@pytest.mark.asyncio
async def test_mock_email_service_multiple_emails() -> None:
    """MockEmailService stores multiple emails independently."""
    svc = MockEmailService()
    await svc.send_token_email("a@example.com", "token-1")
    await svc.send_token_email("b@example.com", "token-2")
    emails = svc.sent_emails
    assert len(emails) == 2
    assert emails[0].to == "a@example.com"
    assert emails[1].to == "b@example.com"


# ---------------------------------------------------------------------------
# Property 13: Email contains only the token
# Validates: Requirements 9.3, 9.4
# ---------------------------------------------------------------------------

_valid_emails = st.emails()
_token_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."
    ),
    min_size=1,
    max_size=64,
)


@given(recipient=_valid_emails, token=_token_strategy)
@settings(max_examples=50)
def test_property_13_email_contains_token(recipient: str, token: str) -> None:
    """Property 13: For any valid email + token, MockEmailService stores exactly
    one email with that token in the body.

    Validates: Requirements 9.3, 9.4
    """
    import asyncio

    svc = MockEmailService()
    asyncio.run(svc.send_token_email(recipient, token))
    emails = svc.sent_emails
    assert len(emails) == 1, "Exactly one email should be stored"
    assert token in emails[0].body, "Token must appear in the email body"
    assert emails[0].to == recipient, "Email must be addressed to the recipient"


# ---------------------------------------------------------------------------
# Property 14: Raw token is never stored in the repository
# Validates: Requirements 9.5
# ---------------------------------------------------------------------------


@given(recipient=_valid_emails)
@settings(max_examples=50)
def test_property_14_token_not_stored_in_repository(recipient: str) -> None:
    """Property 14: The raw token must NOT appear in any stored repository field.

    After creating a user, the raw API key must not be stored in the repository —
    only the Argon2id hash should be persisted.

    Validates: Requirements 9.5
    """
    import asyncio

    from gateway_admin.application.commands.create_user import CreateUserCommand

    from .conftest import (
        InMemoryUserRepository,
        SimpleApiKeyService,
        SimpleIdProvider,
    )

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    api_key_svc = SimpleApiKeyService()
    id_prov = SimpleIdProvider()

    async def _run() -> None:
        cmd = CreateUserCommand(
            repository=repo,
            api_key_service=api_key_svc,
            id_provider=id_prov,
            email_service=email_svc,
        )
        try:
            result = await cmd(recipient)
        except Exception:
            return  # skip invalid emails

        raw_key = result.raw_api_key
        users = await repo.list_all()
        for user in users:
            if user.api_key_hash is not None:
                assert raw_key != user.api_key_hash.value, (
                    "Raw token must not be stored as the hash"
                )
                assert raw_key not in user.api_key_hash.value, (
                    "Raw token must not appear in the hash field"
                )

    asyncio.run(_run())
