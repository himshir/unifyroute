"""Tests for Fireworks.ai adapter."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from router.adapters import FireworksAdapter
from router.adapters import ModelInfo, QuotaInfo


@pytest.fixture
def adapter():
    return FireworksAdapter()


def test_fireworks_adapter_init(adapter):
    assert adapter.provider_name == "fireworks"
    assert adapter.litellm_prefix == "fireworks_ai"


@pytest.mark.asyncio
async def test_list_models_success(adapter):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "accounts/fireworks/models/llama-v3p1-8b-instruct", "context_length": 131072},
            {"id": "accounts/fireworks/models/mixtral-8x7b-instruct", "context_length": 32768},
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        models = await adapter._list_models_impl("fw-test-key")

    assert len(models) == 2
    assert models[0].model_id == "accounts/fireworks/models/llama-v3p1-8b-instruct"
    assert models[0].context_window == 131072
    assert models[1].model_id == "accounts/fireworks/models/mixtral-8x7b-instruct"


@pytest.mark.asyncio
async def test_list_models_auth_failure(adapter):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        models = await adapter._list_models_impl("bad-key")

    assert models == []


@pytest.mark.asyncio
async def test_get_quota_success(adapter):
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        quota = await adapter._get_quota_impl("fw-test-key")

    assert quota.tokens_remaining == 500_000


@pytest.mark.asyncio
async def test_get_quota_failure(adapter):
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        quota = await adapter._get_quota_impl("bad-key")

    assert quota.tokens_remaining == 0


def test_fireworks_listed_in_registry():
    from router.adapters import adapters
    assert "fireworks" in adapters
    assert isinstance(adapters["fireworks"], FireworksAdapter)
