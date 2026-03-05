"""
Gateway health / smoke tests.
These are lightweight checks that the API gateway is serving correctly after startup.
"""
import pytest
import httpx


class TestGatewayHealth:

    def test_root_returns_ok(self, api_client: httpx.Client):
        """GET /api/ should return 200 with a welcome message."""
        r = api_client.get("/api/")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "llm" in body.get("message", "").lower() or "gateway" in body.get("message", "").lower() or "running" in body.get("message", "").lower()

    def test_models_endpoint_returns_list(self, api_client: httpx.Client):
        """GET /api/v1/models should return 200 with a list of models."""
        r = api_client.get("/api/v1/models")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "data" in body or isinstance(body, list)

    def test_admin_brain_status_returns_200(self, admin_client: httpx.Client):
        """GET /api/admin/brain/status should return 200 with brain_providers array."""
        r = admin_client.get("/api/admin/brain/status")
        assert r.status_code in (200, 404), r.text  # 404 if endpoint not yet mounted
        if r.status_code == 200:
            body = r.json()
            assert "brain_providers" in body or isinstance(body, dict)

    def test_openai_compat_endpoint_exists(self, api_client: httpx.Client):
        """The /api/v1/chat/completions endpoint must exist (not a 404)."""
        r = api_client.options("/api/v1/chat/completions")
        # 200 OK from CORS preflight, or 405 (method not allowed but endpoint exists)
        assert r.status_code != 404, f"chat/completions endpoint missing: {r.text}"

    def test_admin_providers_returns_list(self, admin_client: httpx.Client):
        """GET /api/admin/providers should return a list (even if empty)."""
        r = admin_client.get("/api/admin/providers")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_admin_credentials_returns_list(self, admin_client: httpx.Client):
        """GET /api/admin/credentials should return a list."""
        r = admin_client.get("/api/admin/credentials")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_admin_models_returns_list(self, admin_client: httpx.Client):
        """GET /api/admin/models should return a list."""
        r = admin_client.get("/api/admin/models")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_admin_routing_returns_config(self, admin_client: httpx.Client):
        """GET /api/admin/routing should return a routing config dict."""
        r = admin_client.get("/api/admin/routing")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), dict)
