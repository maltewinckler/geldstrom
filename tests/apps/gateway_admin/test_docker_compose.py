"""Smoke tests: docker-compose.yml volume and comment verification.

Validates:
- Requirement 3.1 / 3.2: ./data host path is not mounted into gateway-admin
- Requirement 3.4: old CLI catalog sync comment is no longer present
"""

from pathlib import Path

import yaml

DOCKER_COMPOSE = Path(__file__).parents[3] / "docker-compose.yml"


def _load_compose() -> dict:
    return yaml.safe_load(DOCKER_COMPOSE.read_text())


def test_gateway_admin_has_no_data_volume_mount():
    """Assert ./data does not appear in gateway-admin volumes (Req 3.1, 3.2)."""
    compose = _load_compose()
    service = compose.get("services", {}).get("gateway-admin", {})
    volumes = service.get("volumes", [])
    for vol in volumes:
        assert not str(vol).startswith("./data"), (
            f"gateway-admin still mounts ./data: {vol!r}"
        )


def test_old_cli_catalog_sync_comment_is_absent():
    """Assert the old gw-admin catalog sync CLI comment is gone (Req 3.4)."""
    content = DOCKER_COMPOSE.read_text()
    assert "gw-admin catalog sync /data/fints_institute.csv" not in content, (
        "docker-compose.yml still contains the old CLI catalog sync comment"
    )
