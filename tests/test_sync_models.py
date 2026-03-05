"""
Tests for the /admin/providers/{id}/sync-models endpoint.

Covers:
- Syncing models for a provider with a dummy credential fails gracefully
- Syncing for a nonexistent provider returns 404
- Syncing without credentials returns 400 (no active credentials)
"""
import pytest
import httpx
import uuid


@pytest.fixture(scope="module")
def syncable_provider(admin_client: httpx.Client):
    """Provider with a fake API key credential for sync tests."""
    name = f"sync-prov-{uuid.uuid4().hex[:8]}"
    r = admin_client.post("/api/admin/providers", json={
        "name": name,
        "display_name": "Sync Test Provider",
        "auth_type": "api_key",
        "enabled": True,
    })
    assert r.status_code == 200, r.text
    prov = r.json()

    # Add a fake credential
    cred = admin_client.post("/api/admin/credentials", json={
        "provider_id": prov["id"],
        "label": "sync-test-cred",
        "auth_type": "api_key",
        "secret_key": "sk-fake-sync-key",
        "enabled": True,
    })
    assert cred.status_code == 200

    yield prov
    admin_client.delete(f"/api/admin/providers/{prov['id']}")


class TestSyncModels:

    def test_sync_nonexistent_provider_returns_404(self, admin_client: httpx.Client):
        r = admin_client.post(f"/api/admin/providers/{uuid.uuid4()}/sync-models")
        assert r.status_code == 404

    def test_sync_provider_without_credentials_returns_400(self, admin_client: httpx.Client):
        """Creating a provider with NO credentials and trying to sync returns 400."""
        name = f"nocred-prov-{uuid.uuid4().hex[:6]}"
        r = admin_client.post("/api/admin/providers", json={
            "name": name,
            "display_name": "NoCred Provider",
            "auth_type": "api_key",
            "enabled": True,
        })
        assert r.status_code == 200
        prov_id = r.json()["id"]

        r2 = admin_client.post(f"/api/admin/providers/{prov_id}/sync-models")
        assert r2.status_code == 400
        assert "credentials" in r2.json()["detail"].lower()

        admin_client.delete(f"/api/admin/providers/{prov_id}")

    def test_sync_provider_with_fake_cred_attempts_fetch(
        self, admin_client: httpx.Client, syncable_provider: dict
    ):
        """
        Sync with a real (but fake) credential should attempt fetch.
        Either succeeds (known hardcoded providers) or fails with provider error (500).
        400 and 404 are not acceptable here.
        """
        r = admin_client.post(
            f"/api/admin/providers/{syncable_provider['id']}/sync-models"
        )
        # Possible outcomes:
        # 200 – provider has hardcoded model list (e.g., anthropic, google-antigravity)
        # 500 – provider API returned error for fake key
        assert r.status_code in (200, 500), r.text
