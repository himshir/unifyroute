import pytest
import httpx

class TestCompletionsEndpoint:
    
    def test_chat_completions_unauthorized(self, raw_client: httpx.Client):
        """Without a valid Bearer token, the endpoint should return 401."""
        response = raw_client.post(
            "/api/v1/chat/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": "hello"}],
            }
        )
        assert response.status_code == 401
        data = response.json()
        assert "gateway_error" in str(data)

    def test_chat_completions_unauthorized_stream(self, raw_client: httpx.Client):
        """Without a valid Bearer token, asking for a stream should also return a 401 (not crash)."""
        response = raw_client.post(
            "/api/v1/chat/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True
            }
        )
        assert response.status_code == 401
