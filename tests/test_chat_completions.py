"""
Tests for /v1/chat/completions and /v1/completions endpoints.

These tests validate:
- The request schema is enforced
- Invalid model aliases return 503 (no candidates) or 422 (validation error)
- A valid virtual model alias with no backend models returns 503 with
  a meaningful error (since this is a unit-level integration test without
  real provider credentials)
- The /v1/completions wrapper endpoint follows the same pattern as /v1/chat/completions
"""
import pytest
import httpx


class TestChatCompletionsInput:

    def test_missing_model_rejected(self, api_client: httpx.Client):
        """Request without 'model' field should be rejected as 422."""
        r = api_client.post("/api/v1/chat/completions", json={
            "messages": [{"role": "user", "content": "hello"}],
        })
        assert r.status_code == 422, r.text

    def test_missing_messages_rejected(self, api_client: httpx.Client):
        """Request without 'messages' field should be rejected as 422."""
        r = api_client.post("/api/v1/chat/completions", json={"model": "lite"})
        assert r.status_code == 422, r.text

    def test_empty_model_accepted_but_no_candidates(self, api_client: httpx.Client):
        """Using a virtual model with no configured backends returns a mocked fallback 200 response."""
        r = api_client.post("/api/v1/chat/completions", json={
            "model": "lite",
            "messages": [{"role": "user", "content": "hello"}],
        })
        # 200: either real LLM responded or exhaustion fallback message was returned
        assert r.status_code == 200, r.text

    def test_unknown_alias_via_yaml_returns_error(self, api_client: httpx.Client):
        """An alias not in virtual models and not in routing YAML returns 200 with fallback mock message."""
        r = api_client.post("/api/v1/chat/completions", json={
            "model": "nonexistent-alias-xyz",
            "messages": [{"role": "user", "content": "test"}],
        })
        assert r.status_code == 200, r.text
        assert "We're sorry" in r.text

    def test_unauthenticated_chat_rejected(self, raw_client: httpx.Client):
        r = raw_client.post("/api/v1/chat/completions", json={
            "model": "lite",
            "messages": [{"role": "user", "content": "test"}],
        })
        assert r.status_code in (401, 403), r.text


class TestVirtualModelRouting:
    """
    Tests specifically for the lite/base/thinking virtual model routing logic.
    When no backend models are configured with these tiers, we expect a clear
    error message. When they are configured we verify correct routing behavior.
    """

    @pytest.mark.parametrize("tier", ["lite", "base", "thinking"])
    def test_virtual_model_request_returns_handled_response(
        self, api_client: httpx.Client, tier: str
    ):
        """All three virtual models should be recognized and processed (not 422)."""
        r = api_client.post("/api/v1/chat/completions", json={
            "model": tier,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        })
        # Either 200 (real LLM available or fallback from exhaustion mock)
        assert r.status_code == 200, f"tier={tier}: Unexpected status {r.status_code}: {r.text}"

    def test_virtual_model_exhaustion_fallback(self, api_client: httpx.Client):
        """When a virtual model has no backends (exhausted), it should return a 200 mock response with configured exhaustion_message."""
        r = api_client.post("/api/v1/chat/completions", json={
            "model": "lite",
            "messages": [{"role": "user", "content": "hello"}],
        })
        # If there are no configured backends during this test, it should return 200 with the fallback msg
        assert r.status_code == 200
        body = r.json()
        
        # If actual LLM responded we might see its message, but if exhausted we see the fallback
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        # Either it's a real response or our mock phrase "We're sorry, no models or quota are available right now."
        assert len(content) > 0

    def test_unknown_alias_returns_mock_response(self, api_client: httpx.Client):
        """Routing errors (RuntimeError) now return graceful 200 mock message."""
        r = api_client.post("/api/v1/chat/completions", json={
            "model": "nonexistent-alias-xyz",
            "messages": [{"role": "user", "content": "test"}],
        })
        assert r.status_code == 200
        body = r.json()
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        assert "We're sorry, no models or quota are available" in content


class TestCompletionsEndpoint:
    """Tests for the legacy /v1/completions (text completion) endpoint."""

    def test_completions_missing_model(self, api_client: httpx.Client):
        r = api_client.post("/api/v1/completions", json={
            "prompt": "Hello world",
        })
        assert r.status_code == 422, r.text

    def test_completions_missing_prompt(self, api_client: httpx.Client):
        r = api_client.post("/api/v1/completions", json={
            "model": "lite",
        })
        assert r.status_code == 422, r.text

    def test_completions_delegates_to_chat(self, api_client: httpx.Client):
        """The /v1/completions endpoint should follow the same routing path as /v1/chat/completions."""
        r = api_client.post("/api/v1/completions", json={
            "model": "lite",
            "prompt": "Say hello",
        })
        # Should be 200 OK (real LLM or mocked exhaustion message)
        assert r.status_code == 200, r.text

    def test_completions_unauthenticated(self, raw_client: httpx.Client):
        r = raw_client.post("/api/v1/completions", json={
            "model": "lite",
            "prompt": "test",
        })
        assert r.status_code in (401, 403)

    def test_cost_usd_tracking_for_streams(self, api_client: httpx.Client, admin_client: httpx.Client):
        """Streaming chat completions should correctly log token counts and USD costs, not defaults of 0."""
        # 1. Send streaming chat completions
        stream_r = api_client.post("/api/v1/chat/completions", json={
            "model": "lite",
            "messages": [{"role": "user", "content": "How are you?"}],
            "stream": True,
        })
        
        # We can only test this if we don't get exhaustion. Exhaustion fallback returns 200 now, 
        # but usage isn't tracked the same way, or maybe it returns 0 tokens.
        if stream_r.status_code != 200:
            pytest.skip("No backends available to serve model for stream test.")
            
        # Optional: inspect if it was a fallback response
        chunk_lines = [line for line in stream_r.iter_lines() if line]
        if any("We're sorry, no models or quota" in l for l in chunk_lines):
            pytest.skip("Model was exhausted, skipping cost tracking test.")

        # 2. Query the admin logs for the latest request
        import time
        time.sleep(1) # wait for bg tasks
        logs_r = admin_client.get("/api/admin/logs?limit=5")
        assert logs_r.status_code == 200
        items = logs_r.json().get("items", [])
        
        assert len(items) > 0, "No request logs found for streaming response."
        
        # Find the latest successful stream request
        latest_log = None
        for item in items:
            if "success_stream" in item.get("status", "") or "success" in item.get("status", ""):
                latest_log = item
                break
                
        assert latest_log is not None, "Could not find a successful logged request."
        
        # 3. Assert prompt/completion tokens are not 0 and cost_usd > 0
        assert latest_log["prompt_tokens"] > 0, "Prompt tokens were not calculated for stream."
        assert latest_log["completion_tokens"] > 0, "Completion tokens were not calculated for stream."
        assert latest_log["cost_usd"] > 0.0, "Cost USD was 0.0 for streaming response."
