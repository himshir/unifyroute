import pytest
import httpx
import uuid

class TestKeyReveal:
    def test_reveal_key_returns_hash_prefix(self, admin_client: httpx.Client):
        r_create = admin_client.post("/api/admin/keys", json={
            "label": f"label-reveal-{uuid.uuid4().hex[:6]}",
            "scopes": ["api"],
        })
        assert r_create.status_code == 200
        key_id = r_create.json()["id"]
        
        r_reveal = admin_client.get(f"/api/admin/keys/{key_id}/reveal")
        assert r_reveal.status_code == 200
        reveal_info = r_reveal.json()["reveal_info"]
        assert reveal_info.startswith("sk-...")
        
        # cleanup
        admin_client.delete(f"/api/admin/keys/{key_id}")

    def test_reveal_nonexistent_key_404(self, admin_client: httpx.Client):
        r = admin_client.get(f"/api/admin/keys/{uuid.uuid4()}/reveal")
        assert r.status_code == 404
