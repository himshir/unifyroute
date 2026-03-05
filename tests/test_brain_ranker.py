"""Unit tests for brain.ranker module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_rank_brain_providers_empty():
    """When no brain configs exist, ranking returns empty list."""
    from brain.ranker import rank_brain_providers

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)

    with patch("brain.tester.get_cached_health", return_value=None):
        ranked = await rank_brain_providers(session)

    assert ranked == []


@pytest.mark.asyncio
async def test_rank_prefers_healthy_over_unhealthy():
    """Healthy provider should rank above an unhealthy one with same priority."""
    from brain.ranker import rank_brain_providers

    cred_id_1 = uuid4()
    cred_id_2 = uuid4()

    entry1 = MagicMock()
    entry1.id = uuid4()
    entry1.credential_id = cred_id_1
    entry1.model_id = "model-a"
    entry1.priority = 100
    entry1.enabled = True
    entry1.provider = MagicMock(name="openai")
    entry1.provider.name = "openai"
    entry1.credential = MagicMock()
    entry1.credential.label = "key-a"

    entry2 = MagicMock()
    entry2.id = uuid4()
    entry2.credential_id = cred_id_2
    entry2.model_id = "model-b"
    entry2.priority = 100
    entry2.enabled = True
    entry2.provider = MagicMock()
    entry2.provider.name = "groq"
    entry2.credential = MagicMock()
    entry2.credential.label = "key-b"

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [entry1, entry2]
    session.execute = AsyncMock(return_value=execute_result)

    async def fake_cached_health(cred_id, model_id):
        if cred_id == cred_id_1:
            return {"ok": True, "latency_ms": 100, "message": "OK"}
        return {"ok": False, "latency_ms": 8000, "message": "Failed"}

    with patch("brain.ranker.get_cached_health", side_effect=fake_cached_health):
        with patch("redis.asyncio.from_url"):
            ranked = await rank_brain_providers(session)

    assert len(ranked) == 2
    assert ranked[0].provider == "openai"   # healthy comes first
    assert ranked[1].provider == "groq"
    assert ranked[0].score > ranked[1].score


@pytest.mark.asyncio
async def test_rank_lower_priority_wins():
    """Entry with priority=10 should outrank priority=200 (both healthy)."""
    from brain.ranker import rank_brain_providers

    cred_id_1 = uuid4()
    cred_id_2 = uuid4()

    def _make_entry(cred_id, pname, priority):
        e = MagicMock()
        e.id = uuid4()
        e.credential_id = cred_id
        e.model_id = "model-x"
        e.priority = priority
        e.enabled = True
        e.provider = MagicMock()
        e.provider.name = pname
        e.credential = MagicMock()
        e.credential.label = "key"
        return e

    entry_high = _make_entry(cred_id_1, "openai", 10)
    entry_low = _make_entry(cred_id_2, "groq", 200)

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [entry_high, entry_low]
    session.execute = AsyncMock(return_value=execute_result)

    async def fake_cached_health(cred_id, model_id):
        return {"ok": True, "latency_ms": 100, "message": "OK"}

    with patch("brain.ranker.get_cached_health", side_effect=fake_cached_health):
        with patch("redis.asyncio.from_url"):
            ranked = await rank_brain_providers(session)

    assert ranked[0].provider == "openai"   # priority 10 > priority 200


@pytest.mark.asyncio
async def test_rank_returns_rankedentry_fields():
    """RankedEntry should have all expected fields."""
    from brain.ranker import rank_brain_providers, RankedEntry

    cred_id = uuid4()
    entry = MagicMock()
    entry.id = uuid4()
    entry.credential_id = cred_id
    entry.model_id = "gpt-4o"
    entry.priority = 50
    entry.enabled = True
    entry.provider = MagicMock()
    entry.provider.name = "openai"
    entry.credential = MagicMock()
    entry.credential.label = "my-openai-key"

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [entry]
    session.execute = AsyncMock(return_value=execute_result)

    async def fake_cached_health(cred_id, model_id):
        return {"ok": True, "latency_ms": 250, "message": "OK", "status_code": 200}

    with patch("brain.ranker.get_cached_health", side_effect=fake_cached_health):
        with patch("redis.asyncio.from_url"):
            ranked = await rank_brain_providers(session)

    assert len(ranked) == 1
    r = ranked[0]
    assert isinstance(r, RankedEntry)
    assert r.provider == "openai"
    assert r.model_id == "gpt-4o"
    assert r.health_ok is True
    assert r.latency_ms == 250
    assert 0.0 <= r.score <= 1.0
