"""
Unit tests for brain.tester module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from brain.tester import TestResult, test_all_brain_credentials as run_brain_tests


@pytest.mark.asyncio
async def test_brain_credentials_empty_list():
    """If no configs exist, returns empty list."""
    session = AsyncMock()

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)

    results = await run_brain_tests(session)
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_brain_credentials_healthy_entry():
    """Tests a single healthy credential and returns one TestResult."""
    session = AsyncMock()

    cred_id = uuid4()
    entry = MagicMock()
    entry.id = uuid4()
    entry.credential_id = cred_id
    entry.model_id = "gpt-4o"
    entry.provider.name = "openai"
    entry.provider.base_url = None
    entry.credential.label = "key-1"
    entry.credential.secret_enc = b"enc"
    entry.credential.iv = b"iv"

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [entry]
    session.execute = AsyncMock(return_value=execute_result)

    mock_health = MagicMock()
    mock_health.ok = True
    mock_health.message = "OK"
    mock_health.latency_ms = 100
    mock_health.status_code = 200

    with patch("brain.tester.decrypt_secret", return_value="sk-test"):
        with patch("brain.tester.check_provider_health", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            with patch("brain.tester._cache_health", new_callable=AsyncMock):
                results = await run_brain_tests(session)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, TestResult)
    assert r.ok is True
    assert r.provider == "openai"
    assert r.model_id == "gpt-4o"


@pytest.mark.asyncio
async def test_brain_credentials_unhealthy_entry():
    """Tests a credential that fails health check — still returns a TestResult."""
    session = AsyncMock()

    entry = MagicMock()
    entry.id = uuid4()
    entry.credential_id = uuid4()
    entry.model_id = "llama"
    entry.provider.name = "groq"
    entry.provider.base_url = None
    entry.credential.label = "key-fail"
    entry.credential.secret_enc = b"enc"
    entry.credential.iv = b"iv"

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [entry]
    session.execute = AsyncMock(return_value=execute_result)

    mock_health = MagicMock()
    mock_health.ok = False
    mock_health.message = "Connection refused"
    mock_health.latency_ms = 0
    mock_health.status_code = None

    with patch("brain.tester.decrypt_secret", return_value="sk-bad"):
        with patch("brain.tester.check_provider_health", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            with patch("brain.tester._cache_health", new_callable=AsyncMock):
                results = await run_brain_tests(session)

    assert len(results) == 1
    assert results[0].ok is False


@pytest.mark.asyncio
async def test_get_cached_health_no_redis():
    """get_cached_health returns None when Redis is unavailable."""
    from brain.tester import get_cached_health

    cred_id = uuid4()
    with patch("brain.tester._get_redis") as mock_redis:
        mock_r = AsyncMock()
        mock_r.get = AsyncMock(return_value=None)
        mock_redis.return_value = mock_r

        result = await get_cached_health(cred_id, "gpt-4o")
    assert result is None
