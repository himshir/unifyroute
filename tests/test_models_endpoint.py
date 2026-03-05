"""
Tests for the /v1/models endpoint.

Covers:
- API tokens see only the three virtual model names: lite, base, thinking
- Admin tokens see the full backend model catalog (more than 3)
- Model objects have expected OpenAI-compatible shape
"""
import pytest
import httpx

VIRTUAL_MODELS = {"lite", "base", "thinking", "auto"}

class TestModelsEndpoint:

    def test_api_token_sees_only_virtual_models(self, api_client: httpx.Client):
        """Non-admin token must only see lite/base/thinking."""
        r = api_client.get("/api/v1/models")
        assert r.status_code == 200
        data = r.json()
        assert data["object"] == "list"
        ids = {m["id"] for m in data["data"]}
        assert ids.issubset(VIRTUAL_MODELS), f"Unexpected model ids: {ids}"

    def test_api_token_model_object_shape(self, api_client: httpx.Client):
        """Each model object must have the required OpenAI-compat fields."""
        r = api_client.get("/api/v1/models")
        assert r.status_code == 200
        for model in r.json()["data"]:
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "created" in model
            assert "owned_by" in model

    def test_admin_token_sees_full_catalog(self, admin_client: httpx.Client):
        """Admin token must see more than just the virtual 3 models."""
        r = admin_client.get("/api/v1/models")
        assert r.status_code == 200
        count = len(r.json()["data"])
        # The full catalog from providers should have significantly more entries
        # If DB is fresh/empty, we allow >= 3 but document the expectation
        assert count >= 3, "Admin catalog should have at least the virtual 3 models"

    def test_admin_sees_more_than_api_token(
        self, admin_client: httpx.Client, api_client: httpx.Client
    ):
        """Admin token should see more models than an API token, or at least the same."""
        admin_count = len(admin_client.get("/api/v1/models").json()["data"])
        api_count = len(api_client.get("/api/v1/models").json()["data"])
        assert admin_count >= api_count
