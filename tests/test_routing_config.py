"""
Tests for /admin/routing configuration endpoints.

Covers:
- GET /admin/routing (read YAML config)
- POST /admin/routing (write YAML config)
- Validation rejects invalid YAML
"""
import pytest
import httpx


VALID_YAML = """\
tiers:
  lite:
    strategy: cheapest_available
    min_quota_remaining: 0
    models: []
  base:
    strategy: cheapest_available
    min_quota_remaining: 0
    models: []
  thinking:
    strategy: cheapest_available
    min_quota_remaining: 0
    models: []
"""

INVALID_YAML = """\
tiers:
  bad_entry: [this: is: not: valid: yaml
"""


class TestRoutingConfig:

    def test_get_routing_config(self, admin_client: httpx.Client):
        r = admin_client.get("/api/admin/routing")
        assert r.status_code == 200
        body = r.json()
        assert "yaml_content" in body
        assert isinstance(body["yaml_content"], str)

    def test_post_routing_config_valid_yaml(self, admin_client: httpx.Client):
        """Posting valid YAML must return success."""
        # First read current config to restore after test
        current = admin_client.get("/api/admin/routing").json()["yaml_content"]

        r = admin_client.post("/api/admin/routing", json={"yaml_content": VALID_YAML})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "success"

        # Restore original
        admin_client.post("/api/admin/routing", json={"yaml_content": current})

    def test_post_routing_config_invalid_yaml(self, admin_client: httpx.Client):
        """Posting invalid YAML must return 400."""
        r = admin_client.post("/api/admin/routing", json={"yaml_content": INVALID_YAML})
        assert r.status_code == 400, r.text

    def test_routing_roundtrip(self, admin_client: httpx.Client):
        """Write a config and then read it back to verify persistence."""
        original = admin_client.get("/api/admin/routing").json()["yaml_content"]
        marker = "# test-marker-roundtrip\n"
        new_yaml = VALID_YAML + marker

        admin_client.post("/api/admin/routing", json={"yaml_content": new_yaml})
        readback = admin_client.get("/api/admin/routing").json()["yaml_content"]
        assert "test-marker-roundtrip" in readback

        # Restore
        admin_client.post("/api/admin/routing", json={"yaml_content": original})
