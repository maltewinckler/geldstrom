"""Serialization utilities for FinTS session state."""

import base64
import json
import zlib
from collections.abc import Mapping
from typing import Any


def compress_datablob(magic: bytes, version: int, data: dict) -> bytes:
    """Compress a dictionary into a datablob format."""
    data = dict(data)
    for k, v in data.items():
        if k.endswith("_bin") and v:
            data[k] = base64.b64encode(v).decode("us-ascii")
    serialized = json.dumps(data).encode("utf-8")
    compressed = zlib.compress(serialized, 9)
    return b";".join([magic, b"1", str(version).encode("us-ascii"), compressed])


def decompress_datablob(
    magic: bytes,
    blob: bytes,
    obj: object = None,
) -> tuple[int, Mapping[str, Any]] | None:
    """Decompress a datablob back into a dictionary."""
    if not blob.startswith(magic):
        raise ValueError("Incorrect data blob")
    s = blob.split(b";", 3)
    if len(s) != 4:
        raise ValueError("Incorrect data blob")
    if not s[1].isdigit() or not s[2].isdigit():
        raise ValueError("Incorrect data blob")
    encoding_version = int(s[1].decode("us-ascii"), 10)
    blob_version = int(s[2].decode("us-ascii"), 10)

    if encoding_version != 1:
        raise ValueError(f"Unsupported encoding version {encoding_version}")

    decompressed = zlib.decompress(s[3])
    data = json.loads(decompressed.decode("utf-8"))
    for k, v in data.items():
        if k.endswith("_bin") and v:
            data[k] = base64.b64decode(v.encode("us-ascii"))

    if obj:
        setfunc = getattr(obj, f"_set_data_v{blob_version}", None)
        if not setfunc:
            raise ValueError("Unknown data blob version")
        setfunc(data)
        return None
    else:
        return blob_version, data


__all__ = ["compress_datablob", "decompress_datablob"]
