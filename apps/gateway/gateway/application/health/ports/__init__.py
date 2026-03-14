"""Outbound ports for the health bounded context."""

from .readiness_check import ReadinessCheck

__all__ = ["ReadinessCheck"]
