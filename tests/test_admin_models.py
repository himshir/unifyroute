"""
Tests for /admin/models CRUD endpoints.

Covers:
- List models
- Create model
- Update model (tier, costs, enabled)
- Delete model
"""
import pytest
import httpx
import uuid


@pytest.fixture(scope="module")
def test_provider_for_models(admin_client: httpx.Client):
    """Create a temporary provider to associate models with."""
    name = f"models-test-prov-{uuid.uuid4().hex[:8]}"
    r = admin_client.post("/api/admin/providers", json={
        "name": name,
        "display_name": "Models Test Provider",
        "auth_type": "api_key",
        "enabled": True,
    })
    assert r.status_code == 200, r.text
    prov = r.json()
    yield prov
    admin_client.delete(f"/api/admin/providers/{prov['id']}")


@pytest.fixture()
def created_model(admin_client: httpx.Client, test_provider_for_models: dict):
    """Create a test model, yield it, then delete."""
    r = admin_client.post("/api/admin/models", json={
        "provider_id": test_provider_for_models["id"],
        "model_id": f"test-model-{uuid.uuid4().hex[:6]}",
        "display_name": "Test Base Model",
        "tier": "base",
        "context_window": 128000,
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015,
        "enabled": True,
    })
    assert r.status_code == 200, r.text
    model = r.json()
    yield model
    admin_client.delete(f"/api/admin/models/{model['id']}")


class TestAdminModelsList:

    def test_list_models_returns_list(self, admin_client: httpx.Client):
        r = admin_client.get("/api/admin/models")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestAdminModelCreate:

    def test_create_model_success(
        self, admin_client: httpx.Client, test_provider_for_models: dict
    ):
        mid = f"gpt-test-{uuid.uuid4().hex[:6]}"
        r = admin_client.post("/api/admin/models", json={
            "provider_id": test_provider_for_models["id"],
            "model_id": mid,
            "display_name": "GPT Test Model",
            "tier": "lite",
            "context_window": 128000,
            "input_cost_per_1k": 0.0001,
            "output_cost_per_1k": 0.0003,
            "enabled": True,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["model_id"] == mid
        assert body["tier"] == "lite"
        admin_client.delete(f"/api/admin/models/{body['id']}")

    def test_create_model_invalid_tier(
        self, admin_client: httpx.Client, test_provider_for_models: dict
    ):
        """An unknown tier value should be rejected at the DB level or validation."""
        r = admin_client.post("/api/admin/models", json={
            "provider_id": test_provider_for_models["id"],
            "model_id": "bad-tier-model",
            "display_name": "Bad Tier Model",
            "tier": "ultra",       # not in (lite, base, thinking, '')
            "context_window": 128000,
            "input_cost_per_1k": 0.0,
            "output_cost_per_1k": 0.0,
        })
        # Could be 422 (validation) or 500 (DB constraint). Either signals rejection.
        assert r.status_code in (422, 500), r.text


class TestAdminModelUpdate:

    def test_update_model_tier(
        self, admin_client: httpx.Client, created_model: dict
    ):
        mid = created_model["id"]
        r = admin_client.patch(f"/api/admin/models/{mid}", json={"tier": "thinking"})
        assert r.status_code == 200, r.text
        assert r.json()["tier"] == "thinking"

    def test_update_model_costs(
        self, admin_client: httpx.Client, created_model: dict
    ):
        mid = created_model["id"]
        r = admin_client.patch(f"/api/admin/models/{mid}", json={
            "input_cost_per_1k": 0.002,
            "output_cost_per_1k": 0.004,
        })
        assert r.status_code == 200, r.text

    def test_update_model_disable(
        self, admin_client: httpx.Client, created_model: dict
    ):
        mid = created_model["id"]
        r = admin_client.patch(f"/api/admin/models/{mid}", json={"enabled": False})
        assert r.status_code == 200
        assert r.json()["enabled"] is False
        admin_client.patch(f"/api/admin/models/{mid}", json={"enabled": True})

    def test_update_nonexistent_model(self, admin_client: httpx.Client):
        r = admin_client.patch(
            f"/api/admin/models/{uuid.uuid4()}", json={"enabled": False}
        )
        assert r.status_code == 404


class TestAdminModelDelete:

    def test_delete_model_success(
        self, admin_client: httpx.Client, test_provider_for_models: dict
    ):
        # Create
        r = admin_client.post("/api/admin/models", json={
            "provider_id": test_provider_for_models["id"],
            "model_id": f"del-{uuid.uuid4().hex[:6]}",
            "display_name": "Delete Me",
            "tier": "lite",
            "context_window": 128000,
            "input_cost_per_1k": 0.0,
            "output_cost_per_1k": 0.0,
        })
        assert r.status_code == 200
        mid = r.json()["id"]
        # Delete
        r2 = admin_client.delete(f"/api/admin/models/{mid}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "success"

    def test_delete_nonexistent_model(self, admin_client: httpx.Client):
        r = admin_client.delete(f"/api/admin/models/{uuid.uuid4()}")
        assert r.status_code == 404
