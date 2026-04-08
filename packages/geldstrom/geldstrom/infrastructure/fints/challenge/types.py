"""Core challenge types and value objects for 2FA flows."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from enum import Enum

from pydantic import BaseModel


class ChallengeType(Enum):
    TEXT = "text"
    DECOUPLED = "decoupled"


class ChallengeData(BaseModel, frozen=True):
    """Binary data for visual challenges."""

    mime_type: str | None = None
    data: bytes


class Challenge(metaclass=ABCMeta):
    """Abstract base for protocol-agnostic 2FA challenges."""

    @property
    @abstractmethod
    def challenge_type(self) -> ChallengeType: ...

    @property
    @abstractmethod
    def challenge_text(self) -> str | None: ...

    @property
    @abstractmethod
    def challenge_html(self) -> str | None: ...

    @property
    @abstractmethod
    def challenge_data(self) -> ChallengeData | None: ...

    @property
    @abstractmethod
    def is_decoupled(self) -> bool: ...

    @abstractmethod
    def get_data(self) -> bytes: ...


class ChallengeResult(BaseModel):
    """Result of responding to a 2FA challenge."""

    response: str | None = None
    cancelled: bool = False
    error: str | None = None
    detach: bool = False

    @property
    def is_success(self) -> bool:
        return self.response is not None and not self.cancelled

    @property
    def needs_polling(self) -> bool:
        return self.response is None and not self.cancelled and not self.error


def decode_phototan_image(data: bytes) -> dict:
    """Decode photoTAN data into its mime type and image data."""
    mime_type_length = int.from_bytes(data[:2], byteorder="big")
    mime_type = data[2 : 2 + mime_type_length].decode("iso-8859-1")
    image_length_start = 2 + mime_type_length
    image_length = int.from_bytes(
        data[image_length_start : 2 + image_length_start], byteorder="big"
    )
    image = data[2 + image_length_start : 2 + image_length_start + image_length]
    return {"mime_type": mime_type, "image": image}
