"""Account entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Account(BaseModel, frozen=True):
    """Account aggregate root representing a subscriber.

    An Account owns zero or more ApiKey entities.
    """

    id: UUID
    created_at: datetime
