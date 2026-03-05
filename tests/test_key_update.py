import pytest
import httpx
import uuid

class TestKeyUpdate:
    def test_update_key_label_success(self, admin_client: httpx.Client):
        r_create = admin_client.post("/api/admin/keys", json={
            "label": f"label-to-update-{uuid.uuid4().hex[:6]}",
            "scopes": ["api"],
        })
        assert r_create.status_code == 200
        key_id = r_create.json()["id"]
        
        new_label = f"updated-label-{uuid.uuid4().hex[:6]}"
        r_update = admin_client.patch(f"/api/admin/keys/{key_id}", json={
            "label": new_label
        })
        assert r_update.status_code == 200
        assert r_update.json()["label"] == new_label
        
        # cleanup
        admin_client.delete(f"/api/admin/keys/{key_id}")

    def test_update_key_nonexistent_404(self, admin_client: httpx.Client):
        r = admin_client.patch(f"/api/admin/keys/{uuid.uuid4()}", json={
            "label": "should-fail"
        })
        assert r.status_code == 404

    def test_update_key_empty_label_rejected(self, admin_client: httpx.Client):
        r_create = admin_client.post("/api/admin/keys", json={
            "label": f"empty-test-{uuid.uuid4().hex[:6]}",
            "scopes": ["api"],
        })
        assert r_create.status_code == 200
        key_id = r_create.json()["id"]
        
        r_update = admin_client.patch(f"/api/admin/keys/{key_id}", json={
            "label": "   "
        })
        assert r_update.status_code == 422
        
        # cleanup
        admin_client.delete(f"/api/admin/keys/{key_id}")
