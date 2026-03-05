import httpx
import json
from typing import Dict, Any, List, AsyncGenerator
from shared.security import decrypt_secret
from shared.models import Credential
from .base import ProviderAdapter, ModelInfo, QuotaInfo

_GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _openai_messages_to_gemini(messages: list) -> tuple[list, str | None]:
    """
    Convert OpenAI-style messages to Gemini's `contents` + optional `systemInstruction`.
    Returns (contents, system_instruction_text).
    """
    contents = []
    system_parts = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            system_parts.append({"text": content})
            continue

        gemini_role = "model" if role == "assistant" else "user"
        if isinstance(content, str):
            parts = [{"text": content}]
        elif isinstance(content, list):
            # Multimodal content blocks (not yet fully handled — text only)
            parts = [{"text": p.get("text", "")} for p in content if p.get("type") == "text"]
        else:
            parts = [{"text": str(content)}]

        # Gemini requires alternating user/model turns; merge consecutive same-role
        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"].extend(parts)
        else:
            contents.append({"role": gemini_role, "parts": parts})

    system_text = "\n\n".join(p["text"] for p in system_parts) if system_parts else None
    return contents, system_text


class GeminiResponse:
    """
    Minimal wrapper around a Gemini generateContent response.
    Exposes the same attributes as litellm.ModelResponse so completions.py
    can consume it with `hasattr` checks, and model_dump() for FastAPI serialisation.
    """

    def __init__(self, data: dict, model: str):
        candidates = data.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)

        from types import SimpleNamespace
        self.id = data.get("responseId", "ga-resp")
        self.object = "chat.completion.chunk"
        self.model = model
        
        msg_ns = SimpleNamespace(
            role="assistant",
            content=text,
            function_call=None,
            tool_calls=None,
        )
        
        self.choices = [
            SimpleNamespace(
                index=0,
                finish_reason=(candidates[0].get("finishReason", "stop").lower()
                               if candidates else "stop"),
                message=msg_ns,
                delta=msg_ns
            )
        ]
        self.usage = SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    def model_dump(self) -> dict:
        choice = self.choices[0]
        return {
            "id": self.id,
            "object": self.object,
            "model": self.model,
            "choices": [{
                "index": choice.index,
                "finish_reason": choice.finish_reason,
                "message": {
                    "role": choice.message.role,
                    "content": choice.message.content,
                },
                "delta": {
                    "role": choice.delta.role,
                    "content": choice.delta.content,
                },
            }],
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
            },
        }
        
    def model_dump_json(self) -> str:
        return json.dumps(self.model_dump())


def _gemini_response_to_litellm(data: dict, model: str) -> "GeminiResponse":
    return GeminiResponse(data, model)


class GoogleGeminiAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__("google", "gemini")

    # ------------------------------------------------------------------
    # chat — override to handle OAuth2 tokens via direct REST
    # ------------------------------------------------------------------
    async def chat(self, credential: Credential, messages: list, model: str,
                   stream: bool = False, **kwargs) -> Any:
        api_key = decrypt_secret(credential.secret_enc, credential.iv)

        if credential.auth_type == "oauth2":
            return await self._chat_oauth(credential, api_key, messages, model, stream, **kwargs)

        # api_key auth: delegate to LiteLLM as normal
        return await super().chat(credential, messages, model, stream, **kwargs)

    async def _chat_oauth(self, credential: Credential, access_token: str, messages: list, model: str,
                          stream: bool = False, **kwargs) -> Any:
        """
        Call generateContent directly with Authorization: Bearer <token>.
        Uses the standard Vertex AI endpoint.
        """
        contents, system_text = _openai_messages_to_gemini(messages)

        request_wrapper: dict = {"contents": contents}

        # Inject Antigravity system instruction
        ANTIGRAVITY_SYSTEM_INSTRUCTION = (
            "You are Antigravity, a powerful agentic AI coding assistant designed by the Google Deepmind team working on Advanced Agentic Coding."
            "You are pair programming with a USER to solve their coding task. The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question."
            "**Absolute paths only**"
            "**Proactiveness**"
        )
        parts = [{"text": ANTIGRAVITY_SYSTEM_INSTRUCTION}]
        if system_text:
            parts.append({"text": system_text})
        
        request_wrapper["systemInstruction"] = {
            "role": "user",
            "parts": parts
        }

        # Forward generation config if provided
        gen_config = {}
        if "temperature" in kwargs:
            gen_config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            gen_config["maxOutputTokens"] = kwargs["max_tokens"]
        if gen_config:
            request_wrapper["generationConfig"] = gen_config

        oauth_meta = getattr(credential, "oauth_meta", None) or {}
        project_id = oauth_meta.get("project_id")
        if not project_id:
            raise RuntimeError("OAuth credential is missing project_id")
        
        model_lower = model.lower()
        if "pro" in model_lower:
            gemini_model = "gemini-1.5-pro-002"
        elif "flash" in model_lower:
            gemini_model = "gemini-1.5-flash-002"
        else:
            gemini_model = model

        endpoint_suffix = "streamGenerateContent?alt=sse" if stream else "generateContent"
        endpoint = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{gemini_model}:{endpoint_suffix}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-goog-user-project": project_id
        }

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Using Vertex AI Endpoint: {endpoint}")

        if stream:
            async def _stream_generator():
                async with httpx.AsyncClient() as client:
                    async with client.stream("POST", endpoint, headers=headers, json=request_wrapper) as r:
                         if r.status_code != 200:
                             error_text = await r.aread()
                             raise RuntimeError(f"Vertex AI API error {r.status_code}: {error_text.decode('utf-8')[:300]}")
                         
                         async for line in r.aiter_lines():
                             if line.startswith("data: "):
                                 data_str = line[6:].strip()
                                 if data_str == "[DONE]" or not data_str:
                                     continue
                                 try:
                                     data_json = json.loads(data_str)
                                     yield _gemini_response_to_litellm(data_json, model)
                                 except json.JSONDecodeError:
                                     pass
            return _stream_generator()
        else:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(endpoint, headers=headers, json=request_wrapper)
            if r.status_code != 200:
                raise RuntimeError(f"Vertex AI API error {r.status_code}: {r.text[:300]}")
            return _gemini_response_to_litellm(r.json(), model)

    # ------------------------------------------------------------------
    # list_models
    # ------------------------------------------------------------------
    async def _list_models_impl(self, api_key: str, auth_type: str = "api_key") -> List[ModelInfo]:
        headers = {}
        if auth_type == "oauth2":
            url = f"{_GENAI_BASE}/models"
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            url = f"{_GENAI_BASE}/models?key={api_key}"

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers)
        if r.status_code != 200:
            return []
        models = []
        for m in r.json().get("models", []):
            name = m.get("name", "").replace("models/", "")
            if "generateContent" in m.get("supportedGenerationMethods", []):
                models.append(ModelInfo(
                    model_id=name,
                    display_name=m.get("displayName", name),
                    context_window=m.get("inputTokenLimit", 1_000_000),
                    supports_functions=True,
                ))
        return models

    # ------------------------------------------------------------------
    # get_quota
    # ------------------------------------------------------------------
    async def _get_quota_impl(self, api_key: str, auth_type: str = "api_key") -> QuotaInfo:
        headers = {}
        if auth_type == "oauth2":
            url = f"{_GENAI_BASE}/models?pageSize=1"
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            url = f"{_GENAI_BASE}/models?key={api_key}&pageSize=1"

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers)
        if r.status_code != 200:
            return QuotaInfo(tokens_remaining=0)
        remaining_tokens = r.headers.get(
            "x-ratelimit-remaining-tokens",
            r.headers.get("ratelimit-remaining-tokens", None)
        )
        remaining_requests = r.headers.get(
            "x-ratelimit-remaining-requests",
            r.headers.get("ratelimit-remaining-requests", None)
        )
        return QuotaInfo(
            tokens_remaining=int(remaining_tokens) if remaining_tokens and remaining_tokens.isdigit() else 1_000_000,
            requests_remaining=int(remaining_requests) if remaining_requests and remaining_requests.isdigit() else 1_000,
        )
