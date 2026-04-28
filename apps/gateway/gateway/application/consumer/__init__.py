"""Authentication bounded context for the gateway application layer."""

from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)

__all__ = ["AuthenticateConsumerQuery"]
