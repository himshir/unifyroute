"""
Integration tests for the OAuth routes.
Covers:
- GET /admin/oauth/{provider_id}/start returns redirect or error
- Non-existent provider returns 404
- Unauthenticated access is rejected
"""
import pytest
import httpx
import uuid


class TestOAuthRoutes:

    def test_start_with_nonexistent_provider(self, admin_client: httpx.Client):
        """OAuth start with a non-existent provider ID should return 404."""
        fake_id = str(uuid.uuid4())
        r = admin_client.get(f"/api/admin/oauth/{fake_id}/start")
        assert r.status_code == 404, r.text

    def test_start_unauthenticated(self, raw_client: httpx.Client):
        """OAuth start without a token should return 401 or 403."""
        fake_id = str(uuid.uuid4())
        r = raw_client.get(f"/api/admin/oauth/{fake_id}/start")
        assert r.status_code in (401, 403), r.text

    def test_callback_unauthenticated(self, raw_client: httpx.Client):
        """OAuth callback without a token should return 401 or 403."""
        fake_id = str(uuid.uuid4())
        r = raw_client.get(f"/api/admin/oauth/{fake_id}/callback?code=test&state=test")
        assert r.status_code in (401, 403), r.text

    def test_callback_with_invalid_state(self, admin_client: httpx.Client):
        """OAuth callback with an invalid state token should return 400 or 404."""
        fake_id = str(uuid.uuid4())
        r = admin_client.get(
            f"/api/admin/oauth/{fake_id}/callback",
            params={"code": "test_code", "state": "invalid_state"},
        )
        # 400 bad request, 404 provider not found, or 422 validation error
        assert r.status_code in (400, 404, 422), r.text
