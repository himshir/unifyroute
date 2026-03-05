"""
Tests for /admin/credentials CRUD endpoints.

Covers:
- List credentials
- Create credential for a provider
- Delete credential
- Verify credential (key validation)
- Quota check
"""
import pytest
import httpx
import uuid


@pytest.fixture(scope="module")
def test_provider(admin_client: httpx.Client):
    """Created a throwaway provider to hold test credentials."""
    name = f"cred-test-provider-{uuid.uuid4().hex[:8]}"
    r = admin_client.post("/api/admin/providers", json={
        "name": name,
        "display_name": "Credential Test Provider",
        "auth_type": "api_key",
        "enabled": True,
    })
    assert r.status_code == 200, r.text
    provider = r.json()
    yield provider
    admin_client.delete(f"/api/admin/providers/{provider['id']}")


@pytest.fixture()
def created_credential(admin_client: httpx.Client, test_provider: dict):
    """Creates a credential and removes it after the test."""
    r = admin_client.post("/api/admin/credentials", json={
        "provider_id": test_provider["id"],
        "label": f"cred-{uuid.uuid4().hex[:8]}",
        "auth_type": "api_key",
        "secret_key": "sk-fake-test-key-12345",
        "enabled": True,
    })
    assert r.status_code == 200, r.text
    cred = r.json()
    yield cred
    admin_client.delete(f"/api/admin/credentials/{cred['id']}")


class TestCredentialsList:

    def test_list_credentials_returns_200(self, admin_client: httpx.Client):
        r = admin_client.get("/api/admin/credentials")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestCredentialCreate:

    def test_create_credential_success(
        self, admin_client: httpx.Client, test_provider: dict
    ):
        r = admin_client.post("/api/admin/credentials", json={
            "provider_id": test_provider["id"],
            "label": "test-cred-create",
            "auth_type": "api_key",
            "secret_key": "sk-test-secret",
            "enabled": True,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "id" in body
        assert body["label"] == "test-cred-create"
        assert body["enabled"] is True
        # cleanup
        admin_client.delete(f"/api/admin/credentials/{body['id']}")

    def test_credential_secret_not_exposed(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """The credential response must never return the plaintext secret."""
        assert "secret_key" not in created_credential
        assert "secret_enc" not in created_credential
        assert "secret_plaintext" not in created_credential


class TestCredentialDelete:

    def test_delete_credential(self, admin_client: httpx.Client, test_provider: dict):
        # Create
        r = admin_client.post("/api/admin/credentials", json={
            "provider_id": test_provider["id"],
            "label": "to-be-deleted",
            "auth_type": "api_key",
            "secret_key": "sk-dummy",
        })
        assert r.status_code == 200
        cid = r.json()["id"]
        # Delete
        r2 = admin_client.delete(f"/api/admin/credentials/{cid}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"

    def test_delete_nonexistent_credential(self, admin_client: httpx.Client):
        r = admin_client.delete(f"/api/admin/credentials/{uuid.uuid4()}")
        assert r.status_code == 404


class TestCredentialVerify:

    def test_verify_credential_returns_result(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """Verify endpoint should return a status response even for fake keys."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/verify")
        assert r.status_code == 200, r.text
        body = r.json()
        # Must have status + message keys
        assert "status" in body
        assert "message" in body
        # Either success or error – a fake key is expected to fail
        assert body["status"] in ("success", "error", "info")

    def test_verify_message_is_descriptive(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """Verify message should mention the provider or connection result, not just 'OK'."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/verify")
        assert r.status_code == 200, r.text
        body = r.json()
        msg = body.get("message", "")
        # Should NOT be the raw "OK" from HealthResult — should be descriptive
        assert msg != "OK", f"Expected descriptive message, got plain 'OK'"
        assert len(msg) > 3, f"Message too short to be useful: {msg!r}"

    def test_verify_response_has_latency(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """Verify response must include latency_ms field."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/verify")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "latency_ms" in body

    def test_verify_nonexistent_credential_returns_404(self, admin_client: httpx.Client):
        """Verify endpoint with an unknown ID must return 404."""
        r = admin_client.get(f"/api/admin/credentials/{uuid.uuid4()}/verify")
        assert r.status_code == 404, r.text


class TestCredentialQuota:

    def test_quota_check_returns_200(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """Quota endpoint must return 200 even when no data has been polled."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/quota")
        assert r.status_code == 200, r.text

    def test_quota_response_always_has_tokens_remaining_field(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """tokens_remaining must always be present (null or a number) — never missing, to prevent 'undefined' in the UI."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/quota")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "tokens_remaining" in body, \
            "tokens_remaining key missing — UI will show 'undefined'"

    def test_quota_response_always_has_requests_remaining_field(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """requests_remaining must always be present (null or a number) — never missing."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/quota")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "requests_remaining" in body, \
            "requests_remaining key missing — UI will show 'undefined'"

    def test_quota_no_data_has_message(
        self, admin_client: httpx.Client, created_credential: dict
    ):
        """When no quota data is polled yet, a helpful message field must be present."""
        cid = created_credential["id"]
        r = admin_client.get(f"/api/admin/credentials/{cid}/quota")
        assert r.status_code == 200, r.text
        body = r.json()
        # If tokens_remaining is null, a message should explain why
        if body.get("tokens_remaining") is None:
            assert "message" in body, "No tokens_remaining AND no message — UI has no info to show"
            assert len(body["message"]) > 5, "Message is too short to be useful"

    def test_quota_nonexistent_credential_returns_404(self, admin_client: httpx.Client):
        """Quota endpoint with an unknown ID must return 404."""
        r = admin_client.get(f"/api/admin/credentials/{uuid.uuid4()}/quota")
        assert r.status_code == 404, r.text


class TestSyncModels:

    def test_sync_models_returns_200(
        self, admin_client: httpx.Client, test_provider: dict
    ):
        """POST /admin/providers/{id}/sync-models should return 200 and trigger sync."""
        pid = test_provider["id"]
        r = admin_client.post(f"/api/admin/providers/{pid}/sync-models")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "status" in body
        assert "total" in body
        assert "inserted" in body

    def test_sync_models_response_has_descriptive_message(
        self, admin_client: httpx.Client, test_provider: dict
    ):
        """sync-models response should have a human-readable message field."""
        pid = test_provider["id"]
        r = admin_client.post(f"/api/admin/providers/{pid}/sync-models")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "message" in body
        assert len(body["message"]) > 5

    def test_sync_models_nonexistent_provider_returns_404(self, admin_client: httpx.Client):
        """sync-models with unknown provider ID should return 404."""
        r = admin_client.post(f"/api/admin/providers/{uuid.uuid4()}/sync-models")
        assert r.status_code == 404, r.text
