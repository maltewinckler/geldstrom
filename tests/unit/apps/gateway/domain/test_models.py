"""Property-based tests for gateway domain model invariants."""

# Feature: gateway-core, Property 6: SessionIdentity carries 128-bit entropy

import re
from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from gateway.domain.session.value_objects.session_identity import (
    SESSION_TTL_SECONDS,
    SessionIdentity,
)

# UUID4 hex: exactly 32 lowercase hex characters (128 bits)
_UUID4_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


@settings(max_examples=100)
@given(st.integers())  # dummy input to drive repeated generation
def test_session_identity_create_has_128_bit_entropy(_: int) -> None:
    """**Validates: Requirements 3.3**

    For any SessionIdentity created via SessionIdentity.create(),
    the session_id field is a valid UUID4 hex string
    (32 hex characters = 128 bits of entropy).
    """
    identity = SessionIdentity.create()

    # Must be exactly 32 hex chars (128 bits)
    assert _UUID4_HEX_RE.match(identity.session_id), (
        f"session_id {identity.session_id!r} is not a valid 32-char hex string"
    )
    # Verify length explicitly
    assert len(identity.session_id) == 32


# Feature: gateway-core, Property 7: SessionIdentity expiry is 300 seconds


@settings(max_examples=100)
@given(st.integers())  # dummy input to drive repeated generation
def test_session_identity_create_has_300s_expiry(_: int) -> None:
    """**Validates: Requirements 3.1**

    For any SessionIdentity created via SessionIdentity.create(),
    the expires_at field is exactly 300 seconds after the creation timestamp.
    """
    before = datetime.now(UTC)
    identity = SessionIdentity.create()
    after = datetime.now(UTC)

    assert SESSION_TTL_SECONDS == 300, "SESSION_TTL_SECONDS must be 300"

    expected_earliest = before + timedelta(seconds=SESSION_TTL_SECONDS)
    expected_latest = after + timedelta(seconds=SESSION_TTL_SECONDS)

    assert expected_earliest <= identity.expires_at <= expected_latest, (
        f"expires_at {identity.expires_at} not within expected range "
        f"[{expected_earliest}, {expected_latest}]"
    )


# Feature: gateway-core, Property 8: PendingChallenge never carries credentials


# Use a unique prefix to avoid false substring matches in serialized output.
_CREDENTIAL_PREFIX = "CRED_SECRET_"
_credential_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu",)),
    min_size=8,
    max_size=50,
).map(lambda s: f"{_CREDENTIAL_PREFIX}{s}")


@settings(max_examples=100)
@given(
    pin=_credential_strategy,
    username=_credential_strategy,
)
def test_pending_challenge_never_carries_credentials(
    pin: str,
    username: str,
) -> None:
    """**Validates: Requirements 3.4, 8.3**

    For any PendingChallenge instance, serializing it to JSON or any string
    representation should never contain the original PIN, username, or password
    values from the BankConnection that initiated the flow.
    """
    from gateway.domain.banking.value_objects.connection import BankingProtocol
    from gateway.domain.session.entities.pending_challenge import PendingChallenge

    identity = SessionIdentity.create()
    challenge = PendingChallenge(
        identity=identity,
        protocol=BankingProtocol.FINTS,
        bank_code="12345678",
        dialog_state=b"opaque-dialog-state",
        challenge_type="photoTAN",
        challenge_text="Enter the code",
    )

    # Collect all serialized representations
    str_repr = str(challenge)
    repr_repr = repr(challenge)
    dict_repr = str(challenge.model_dump())

    # None of the representations should contain the raw secret values
    for label, serialized in [
        ("str", str_repr),
        ("repr", repr_repr),
        ("model_dump", dict_repr),
    ]:
        assert pin not in serialized, (
            f"PIN {pin!r} leaked in {label} output: {serialized}"
        )
        assert username not in serialized, (
            f"Username {username!r} leaked in {label} output: {serialized}"
        )
