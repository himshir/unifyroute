"""
Tests for authentication and authorization.

Covers:
- Unauthenticated requests are rejected with HTTP 403/401
- Invalid tokens are rejected with HTTP 401
- Valid admin tokens can access admin endpoints
- Valid API tokens can access public endpoints but not admin endpoints
"""
import pytest
import httpx


class TestAuthentication:

    def test_unauthenticated_rejected_models(self, raw_client: httpx.Client):
        """GET /v1/models without a token must return 401 or 403."""
        r = raw_client.get("/api/v1/models")
        assert r.status_code in (401, 403), r.text

    def test_unauthenticated_rejected_admin(self, raw_client: httpx.Client):
        """GET /admin/providers without a token must return 401 or 403."""
        r = raw_client.get("/api/admin/providers")
        assert r.status_code in (401, 403), r.text

    def test_unauthenticated_rejected_chat(self, raw_client: httpx.Client):
        """POST /v1/chat/completions without token must return 401 or 403."""
        r = raw_client.post("/api/v1/chat/completions", json={"model": "lite", "messages": []})
        assert r.status_code in (401, 403), r.text

    def test_invalid_token_rejected(self, raw_client: httpx.Client):
        """A random invalid bearer token must return 401."""
        r = raw_client.get(
            "/api/v1/models",
            headers={"Authorization": "Bearer sk-totally-invalid-token"}
        )
        assert r.status_code == 401, r.text

    def test_admin_token_accepted_on_admin_route(self, admin_client: httpx.Client):
        """Admin token must be accepted for /admin/* routes."""
        r = admin_client.get("/api/admin/providers")
        assert r.status_code == 200, r.text

    def test_api_token_accepted_on_models_route(self, api_client: httpx.Client):
        """Standard API token must be accepted for /v1/models."""
        r = api_client.get("/api/v1/models")
        assert r.status_code == 200, r.text

    def test_api_token_rejected_on_admin_routes(self, api_client: httpx.Client):
        """API tokens do not have admin scope, so they get 403 on admin routes."""
        r = api_client.get("/api/admin/providers")
        assert r.status_code == 403, r.text

    def test_api_token_rejected_on_admin_keys(self, api_client: httpx.Client):
        r = api_client.get("/api/admin/keys")
        assert r.status_code == 403, r.text
