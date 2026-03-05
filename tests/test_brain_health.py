"""Unit tests for brain.health module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from brain.health import check_endpoint, check_provider_health, HealthResult


@pytest.mark.asyncio
async def test_check_endpoint_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_client

        result = await check_endpoint("https://example.com/v1/models", {"Authorization": "Bearer key"})

    assert result.ok is True
    assert result.status_code == 200
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_check_endpoint_401():
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_client

        result = await check_endpoint("https://example.com/v1/models", {})

    assert result.ok is False
    assert result.status_code == 401


@pytest.mark.asyncio
async def test_check_endpoint_network_error():
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))
        mock_cls.return_value = mock_client

        result = await check_endpoint("https://unreachable.example.com", {})

    assert result.ok is False
    assert "connection" in result.message.lower() or "reach" in result.message.lower() or "refused" in result.message.lower()


@pytest.mark.asyncio
async def test_check_provider_health_openai():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_client

        result = await check_provider_health("openai", "sk-test-key")

    assert result.ok is True


@pytest.mark.asyncio
async def test_check_provider_health_anthropic_uses_custom_headers():
    """Anthropic uses x-api-key header, not Bearer."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    captured_headers = {}

    async def fake_get(url, headers=None, **kwargs):
        captured_headers.update(headers or {})
        return mock_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get
        mock_cls.return_value = mock_client

        result = await check_provider_health("anthropic", "test-key")

    assert "x-api-key" in captured_headers
    assert captured_headers["x-api-key"] == "test-key"
    assert result.ok is True


@pytest.mark.asyncio
async def test_check_provider_health_fireworks():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_client

        result = await check_provider_health("fireworks", "fw-test-key")

    assert result.ok is True


@pytest.mark.asyncio
async def test_check_provider_health_unknown_provider_uses_fallback():
    """Unknown providers get a generic https://api.{name}.com/v1/models URL."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    captured_url = []

    async def fake_get(url, headers=None, **kwargs):
        captured_url.append(url)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = fake_get
        mock_cls.return_value = mock_client

        result = await check_provider_health("myprovider", "key123")

    assert captured_url[0] == "https://api.myprovider.com/v1/models"
