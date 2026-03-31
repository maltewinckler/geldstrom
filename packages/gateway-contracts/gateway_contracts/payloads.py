"""Typed NOTIFY payload schemas shared by gateway and admin CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ConsumerUpdatedPayload:
    """Payload for the consumer_updated NOTIFY channel."""

    consumer_id: str

    def serialize(self) -> str:
        return json.dumps({"consumer_id": self.consumer_id})

    @classmethod
    def deserialize(cls, raw: str) -> ConsumerUpdatedPayload:
        data = json.loads(raw)
        consumer_id = data.get("consumer_id")
        if not isinstance(consumer_id, str):
            raise ValueError("consumer_id must be a string")
        return cls(consumer_id=consumer_id)
