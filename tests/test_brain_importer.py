"""Unit tests for brain.importer module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from brain.importer import ImportResult, import_from_yaml_str, import_from_json_str, import_from_dict


# --- Helpers ---

def _make_session_mock(provider=None, credential=None, existing_models=None):
    """Build a minimal async SQLAlchemy session mock."""
    session = AsyncMock()

    # execute() returns a mock result
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = provider
    execute_result.scalars.return_value.first.return_value = credential

    # fetchall() for existing models
    existing = existing_models or []
    fetch_mock = MagicMock()
    fetch_mock.fetchall.return_value = [(m,) for m in existing]
    execute_result.fetchall.return_value = [(m,) for m in existing]

    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    return session


@pytest.mark.asyncio
async def test_import_from_yaml_str_valid():
    """Valid YAML with one provider and no credentials returns ImportResult."""
    yaml_content = """
providers:
  - name: fireworks
    credentials: []
    models: []
"""
    session = AsyncMock()

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None  # provider not found → create
    execute_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    result = await import_from_yaml_str(yaml_content, session)
    assert "fireworks" in result.providers_created
    assert not result.errors


@pytest.mark.asyncio
async def test_import_from_yaml_str_invalid_yaml():
    yaml_content = ": this is: not: valid: yaml: ["
    session = AsyncMock()
    result = await import_from_yaml_str(yaml_content, session)
    assert result.errors
    assert any("yaml" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_import_from_json_str_valid():
    json_content = '{"providers": [{"name": "groq", "credentials": [], "models": []}]}'
    session = AsyncMock()

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    execute_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    result = await import_from_json_str(json_content, session)
    assert "groq" in result.providers_created


@pytest.mark.asyncio
async def test_import_from_json_str_invalid():
    json_content = "{not valid json"
    session = AsyncMock()
    result = await import_from_json_str(json_content, session)
    assert result.errors


@pytest.mark.asyncio
async def test_import_skips_existing_provider():
    """If provider already exists, it should be skipped."""
    existing_provider = MagicMock()
    existing_provider.id = "provider-uuid-123"

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = existing_provider
    execute_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    data = {"providers": [{"name": "openai", "credentials": [], "models": []}]}
    result = await import_from_dict(data, session)
    assert "openai" in result.providers_skipped
    assert "openai" not in result.providers_created


@pytest.mark.asyncio
async def test_import_missing_name_records_error():
    data = {"providers": [{"credentials": [], "models": []}]}
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    result = await import_from_dict(data, session)
    assert result.errors


@pytest.mark.asyncio
async def test_import_credential_missing_api_key():
    session = AsyncMock()
    existing_provider = MagicMock()
    existing_provider.id = "prov-id"

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = existing_provider
    execute_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    data = {"providers": [{"name": "openai", "credentials": [{"label": "key1"}], "models": []}]}
    result = await import_from_dict(data, session)
    assert any("api_key" in e for e in result.errors)
