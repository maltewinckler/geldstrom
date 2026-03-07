"""Session domain — challenge/TAN flow aggregate, ports, and value objects.

Sub-packages:
  entities/      — PendingChallenge (aggregate root)
  value_objects/ — SessionIdentity, FetchStatus, ChallengeInfo, FetchResult,
                   AuditEvent, ApiKeyValidationResult
  ports/         — ChallengeRepository, ApiKeyValidator, AuditEventPublisher
"""

from gateway.domain.session.entities.pending_challenge import PendingChallenge
from gateway.domain.session.ports.repository import ChallengeRepository
from gateway.domain.session.ports.services import ApiKeyValidationResult as _AKVRAlias
from gateway.domain.session.ports.services import ApiKeyValidator, AuditEventPublisher
from gateway.domain.session.value_objects.audit import (
    ApiKeyValidationResult,
    AuditEvent,
)
from gateway.domain.session.value_objects.fetch_result import (
    ChallengeInfo,
    FetchResult,
    FetchStatus,
)
from gateway.domain.session.value_objects.session_identity import (
    SESSION_TTL_SECONDS,
    SessionIdentity,
)

# Resolve the forward reference in FetchResult so Pydantic can validate
# pending_challenge: PendingChallenge at runtime.
FetchResult.model_rebuild()

__all__ = [
    "SESSION_TTL_SECONDS",
    "ApiKeyValidationResult",
    "ApiKeyValidator",
    "AuditEvent",
    "AuditEventPublisher",
    "ChallengeInfo",
    "ChallengeRepository",
    "FetchResult",
    "FetchStatus",
    "PendingChallenge",
    "SessionIdentity",
]
