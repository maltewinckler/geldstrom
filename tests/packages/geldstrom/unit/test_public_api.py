"""Public-surface regression tests for the geldstrom package."""

from __future__ import annotations

import tomllib
from pathlib import Path

import geldstrom


def test_top_level_exports_cover_documented_api() -> None:
    expected_exports = {
        "Challenge",
        "ChallengeData",
        "ChallengeHandler",
        "ChallengeResult",
        "ChallengeType",
        "DecoupledTANPending",
        "FinTS3Client",
        "FinTS3ClientDecoupled",
        "FinTSSessionState",
        "PollResult",
        "SessionToken",
        "TANConfig",
        "TANMethod",
    }

    missing = sorted(name for name in expected_exports if not hasattr(geldstrom, name))
    assert missing == []


def test_package_version_matches_pyproject() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    pyproject = repo_root / "packages" / "geldstrom" / "pyproject.toml"
    package_version = tomllib.loads(pyproject.read_text())["project"]["version"]

    assert geldstrom.version == package_version
    assert geldstrom.__version__ == package_version
