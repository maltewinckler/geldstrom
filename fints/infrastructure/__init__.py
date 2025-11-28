"""Infrastructure adapters for the read-only FinTS architecture."""

__all__ = ["FinTSReadOnlyGateway"]


def __getattr__(name):  # pragma: no cover - simple lazy import shim
    if name == "FinTSReadOnlyGateway":
        from .gateway import FinTSReadOnlyGateway

        return FinTSReadOnlyGateway
    raise AttributeError(name)
